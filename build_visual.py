from bokeh.plotting import figure, output_file, save
from bokeh.models import Select, TextInput, Button, ColumnDataSource, CustomJS, LabelSet, Div
from bokeh.layouts import column, row
output_file('visual.html', title='Spacerocks and the (more or less) famous people lending their names to them')

import pandas as pd
import requests

df = pd.read_csv('data.csv', index_col=0)
edit_counts = pd.read_csv('edit_counts.csv', index_col=0)
df['wikiEdits'] = df['articleName'].apply(lambda x: edit_counts['wikiEdits'][x])
ds = ColumnDataSource({key: list(col) for key, col in df.iteritems()})

TOOLTIPS = [
    ("Asteroid", "@spacerockLabel"),
    ("Named after", "@namesakeLabel"),
]

p = figure(plot_width=750, plot_height=750, title='Magnitude vs Fame',
           toolbar_location='right', tools='box_zoom, tap, box_select, lasso_select, reset', x_axis_type="log", tooltips=TOOLTIPS)

c = p.circle(x='wikiEdits', y='avgMagnitude', size=5, alpha=0.8, source=ds)
p.y_range.flipped = True
p.xaxis[0].axis_label = 'Total number of edits on the Wikipedia article of the namesake of the spacerock'
p.yaxis[0].axis_label = 'Absolute magnitude of the piece of spacerock'

opts = list(set(ds.data['namesakeLabel']))

callback_select = CustomJS(args=dict(ds=ds), code="""
    var namesakes = ds.data['namesakeLabel'];
    var ind = namesakes
          .map((n, i) => n === cb_obj.value ? i : -1)
          .filter(index => index !== -1);;
    ds.selected.indices = ind;
    """)

s = Select(options=['Select person...'] + opts)
s.js_on_change('value', callback_select)

callback_ti = CustomJS(args=dict(ds=ds, s=s, opts=opts), code=f"""
        s.options = opts
            .filter(i => i.toLowerCase().includes(cb_obj.value.toLowerCase()));
        s.value = s.options[0]
        var namesakes = ds.data['namesakeLabel'];
        var ind = namesakes
              .map((n, i) => n === s.value ? i : -1)
              .filter(index => index !== -1);;
        ds.selected.indices = ind;
        """)

ti = TextInput(title="Select to view a specific person", placeholder='Enter filter',
               callback=callback_ti)

callback_reset = CustomJS(args=dict(s=s, ti=ti, opts=opts), code="""
    ti.value = "";
    s.options = ['Select person...'].concat(opts);
    s.value = 'Select person...';
    """)

reset_button = Button(label="Reset", callback=callback_reset)

gender_header = Div(text="<b>Number of asteroids by gender</b><br /> Click to filter",)

counts = df[['namesakeGender', 'spacerockLabel']].groupby('namesakeGender').count()
counts.sort_values('spacerockLabel', inplace=True)
counts = ColumnDataSource(counts)

gender_plot = figure(
    plot_width=300,
    plot_height=100,
    toolbar_location=None,
    tools="tap,box_select",
    y_minor_ticks=len(counts.data['namesakeGender']),
    x_range=[0, 1.2*max(counts.data['spacerockLabel'])],
    y_range = counts.data['namesakeGender'],
    )

gender_plot.xaxis.visible = False
gender_plot.xgrid.visible = False
gender_plot.ygrid.visible = False

labels = LabelSet(x='spacerockLabel', y='namesakeGender', text='spacerockLabel', level='glyph',
        x_offset=2, text_baseline='middle', text_font_size="10px", source=counts)

gender_plot.hbar(
    y='namesakeGender',
    height=0.5, left=0,
    right='spacerockLabel',
    source=counts,
)

gender_plot.add_layout(labels)

#Add callback for gender selection
callback_gender_select = CustomJS(args=dict(ds=ds, counts=counts), code="""
        var genders = ds.data['namesakeGender'];
        ds.selected.indices = [];
        for (var i = 0; i < counts.selected.indices.length; ++i) {
            var selected_gender = counts.data['namesakeGender'][counts.selected.indices[i]];
            var ind = genders
                  .map((n, i) => n === selected_gender ? i : -1)
                  .filter(index => index !== -1);
            ds.selected.indices = ds.selected.indices.concat(ind);
        }
    """)

counts.selected.js_on_change('indices', callback_gender_select)

details_placeholder = "<p>Select a datapoint to view details.</p>"
details = Div(text=details_placeholder)

callback_datapoint_select = CustomJS(
    args=dict(ds=ds, details=details, details_placeholder=details_placeholder),
    code="""
        var ind = ds.selected.indices;
        if (ind.length === 1) {
            var articleName = ds.data['articleName'][ind];
            var spacerockLabel = ds.data['spacerockLabel'][ind];
            var namesakeLabel = ds.data['namesakeLabel'][ind];
            fetch('https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts|pageimages&exintro=1&explaintext=1&pithumbsize=250&origin=*&titles=' + articleName)
                .then(function(response) {
                    return response.json();
                })
                .then(function(myJson) {
                    return myJson['query']['pages'];
                })
                .then(function(pages) {
                    var page = pages[Object.keys(pages)[0]];
                    var pageInfo = {'text': page['extract'].split('\\n')[0]};
                    if (page['thumbnail']) {
                        pageInfo['img'] = page['thumbnail']['source'];
                    }
                    return pageInfo;
                    /*return pages[Object.keys(pages)[0]]['extract'].split('\\n')[0];*/
                })
                .then(function (page) {
                    var regex = /\\(.*? (is|was)/;
                    var cleaned_text = page.text.replace(regex, '$1');
                    var shortened_text = cleaned_text.substring(0, 400);
                    shortened_text = shortened_text.substring(0, shortened_text.lastIndexOf('.') + 1);
                    var imgTag = '';
                    if (page.img) {
                        imgTag = `<img width=250 src=${page.img} />`;
                    }
                    var html = `<p><b>${spacerockLabel.replace(/\\s/g, '&nbsp;')}</b>
                                named&nbsp;after <b>${namesakeLabel.replace(/\\s/g, '&nbsp;')}</b></p>
                                ${imgTag}
                                <p>${shortened_text}</p><p>Source: Wikipedia.
                                <a href="https://en.wikipedia.org/wiki/${articleName}" target=new>Read more...</a></p>`;
                    details.text = html;
                });
        }
        else if (ind.length > 1) {
            details.text = `<p>${ind.length} selected.</p><p>Select one datapoint to view details.</p>`;
        }
        else {
            details.text = details_placeholder;
        }
    """)

ds.selected.js_on_change('indices', callback_datapoint_select)

# Special groups select

def run_wikidata_query(q):
    url = 'https://query.wikidata.org/sparql'
    r = requests.get(url, params = {'format': 'json', 'query': q})
    data = r.json()
    var = data['head']['vars'][0]
    return list(map(
        lambda x: x[var]['value'],
        data['results']['bindings']))


special_groups_queries = {
    'Apollo 11 Crew': """
        select ?entity
        where {
          ?entity wdt:P5096 wd:Q43653.
          service wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'Astronauts': """
        select ?namesake
        where {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P106 wd:Q11631.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'Baseball players': """
        select ?namesake
        where {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P106 wd:Q10871364.
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'The Beatles': """
        select ?entity
        where {
          ?entity p:P361 ?band.
          ?entity wdt:P31 wd:Q5.
          ?band ps:P361 wd:Q1299;
                pq:P580 ?startTime;
                pq:P582 ?endTime.
          filter (year(?endTime) > 1963).
          service wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'Chess Grandmasters': """
        select ?namesake
        where
        {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P2962 wd:Q105269.
          service wikibase:label { bd:serviceParam wikibase:language "[auto_language],en". }
        }""",
    'Ice hockey players': """
        select ?namesake ?namesakeLabel
        where
        {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P106 wd:Q11774891.
          service wikibase:label { bd:serviceParam wikibase:language "[auto_language],en". }
        }""",
    'Musicians': """
        select ?namesake ?namesakeLabel
        where
        {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P106 wd:Q639669.
          service wikibase:label { bd:serviceParam wikibase:language "[auto_language],en". }
        }""",
    'Nobel laureates': """
        select ?entity
        where {
          ?entity wdt:P166 ?award.
          ?award wdt:P31 wd:Q7191.
          service wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'Roman emperors': """
        select ?entity
        where {
          ?entity wdt:P39 wd:Q842606.
          service wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
    'Samurai': """
        select ?namesake
        where
        {
          ?spacerock wdt:P138 ?namesake.
          ?namesake wdt:P31 wd:Q5.
          ?spacerock wdt:P31 wd:Q3863.
          ?namesake wdt:P106 wd:Q38142.
          service wikibase:label { bd:serviceParam wikibase:language "[auto_language],en". }
        }""",
    'US Presidents': """
        select ?entity
        where {
          ?entity wdt:P39 wd:Q11696.
          service wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""",
}

special_groups_members = {'Select...': []}
special_groups_members.update({
    k: run_wikidata_query(q) for k, q in special_groups_queries.items()})



special_groups_sel = Select(options=list(special_groups_members), title="Select to view a special group of people",)

cb_select_group = CustomJS(args=dict(ds=ds, special_groups_members=special_groups_members), code="""
    var namesakes = ds.data['namesake'];
    var selected_group = cb_obj.value;
    var selected_namesakes = special_groups_members[selected_group];
    var ind = [];
    for (var i = 0; i < selected_namesakes.length; ++i) {
        ind = ind.concat(namesakes
              .map((n, j) => n === selected_namesakes[i] ? j : -1)
              .filter(index => index !== -1));
    }
    ds.selected.indices = ind;
""")

special_groups_sel.js_on_change('value', cb_select_group)

title_block = Div(text="""
    <h2>Spacerocks and the (more or less) famous people lending their names to them</h2>
    <p>This visualization was created to explore if larger asteroids are named
    after more famous people. Please use the interactive elements to explore this
    odd collection of people or read more about how and why I made this below.</p>
""")

intro_block = Div(text="""
    <p>When it was announced that Scott Manley would get to lend his name to them
    asteroid 33434 Scottmanley he tweeted a <a href="https://twitter.com/DJSnM/status/1132087769973440512" target=new>
    series of tweets</a> claiming that there seems to be no correlation between
    fame and the size of the spacerock bearing your name. I wanted to explore this
    further so I created this visualization.</p>

    <p>Asteroid size is typically measured as absolute magnitude. This is a
    logarithmic scale and has the odd property that a larger asteroid has a
    smaller number. Fame is much harder to measure. Manley suggested to plot
    magnitude vs record sales, but it seems unnecessarily restrictive to only
    include musicians in the comparison. Instead I turned to the literature and
    found that the <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6034871/" target=new>
    number of edits to a person's Wikipedia article seems to correlate well with
    reconition</a>. Bingo, that was the measure I needed!</p>

    <p>The visualization was made using the <a href="https://bokeh.pydata.org" target=new>
    Bokeh library</a>. Most of the data comes from <a href="https://www.wikidata.org/" target=new>
    Wikidata</a>, except edit counts that were downloaded using the
    <a href="https://xtools.readthedocs.io/en/stable/api/index.html" target=new>
    Xtools API</a>.</p>
""")

filter_header = Div(text="<b>Use filters to explore</b>",)
details_header = Div(text="<b>Details</b>",)

save(
    column(
        title_block,
        row(
            column(filter_header, ti, s, reset_button, special_groups_sel, gender_header, gender_plot),
            p,
            column(details_header, details),
        ),
        intro_block,
    )
)
