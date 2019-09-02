from bokeh.plotting import figure, output_file, save
from bokeh.models import Select, TextInput, Button, ColumnDataSource, CustomJS, LabelSet, Div
from bokeh.layouts import column, row
output_file('visual.html')

import pandas as pd

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
            fetch('https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&exintro=1&explaintext=1&origin=*&titles=' + articleName)
                .then(function(response) {
                    return response.json();
                })
                .then(function(myJson) {
                    return myJson['query']['pages'];
                })
                .then(function(pages) {
                    return pages[Object.keys(pages)[0]]['extract'].split('\\n')[0];
                })
                .then(function (text) {
                    var regex = /\\(.*? (is|was)/;
                    var cleaned_text = text.replace(regex, '$1');
                    var shortened_text = cleaned_text.substring(0, 400);
                    shortened_text = shortened_text.substring(0, shortened_text.lastIndexOf('.') + 1);
                    var html = `<p><b>${spacerockLabel.replace(/\\s/g, '&nbsp;')}</b>
                                named&nbsp;after <b>${namesakeLabel.replace(/\\s/g, '&nbsp;')}</b></p>
                                <p>${shortened_text}</p><p>Source: Wikipedia.
                                <a href="https://en.wikipedia.org/wiki/${articleName}" target=new>Read more...</a></p>`;
                    details.text = html;
                });
        }
        else {
            details.text = details_placeholder;
        }
    """)

ds.selected.js_on_change('indices', callback_datapoint_select)

save(row(column(ti, s, reset_button, gender_header, gender_plot), p, details))
