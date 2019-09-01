from bokeh.plotting import figure, output_file, save
from bokeh.models import Select, TextInput, ColumnDataSource, CustomJS
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

p = figure(plot_width=800, plot_height=800, title="Magnitude vs Fame",
           toolbar_location=None, tools="", x_axis_type="log", tooltips=TOOLTIPS)

c = p.circle(x='wikiEdits', y='avgMagnitude', size=5, alpha=0.6, source=ds)

opts = list(set(ds.data['namesakeLabel']))

callback_select = CustomJS(args=dict(ds=ds), code="""
    var namesakes = ds.data['namesakeLabel'];
    var ind = namesakes
          .map((n, i) => n === cb_obj.value ? i : -1)
          .filter(index => index !== -1);;
    ds.selected.indices = ind;
    """)

s = Select(options=opts)
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
save(row(column(ti, s), p))
