from bokeh.plotting import figure, output_file, show
from bokeh.models import Select, TextInput, ColumnDataSource, CustomJS
from bokeh.layouts import column, row
output_file('visual.html')

import pandas as pd

df = pd.read_csv('data.csv', index_col=0)
edit_counts = pd.read_csv('edit_counts.csv', index_col=0)
df['wikiEdits'] = df['articleName'].apply(lambda x: edit_counts['wikiEdits'][x])

TOOLTIPS = [
    ("Asteroid", "@spacerockLabel"),
    ("Named after", "@namesakeLabel"),
]

p = figure(plot_width=800, plot_height=800, title="Magnitude vs Fame",
           toolbar_location=None, tools="", x_axis_type="log", tooltips=TOOLTIPS)

p.circle(x='wikiEdits', y='avgMagnitude', size=5, alpha=0.6, source=df)

show(p)
