import requests
import pandas as pd

URL = 'https://query.wikidata.org/sparql'
QUERY = """
SELECT ?spacerock ?spacerockLabel (AVG(?magnitude) AS ?avgMagnitude) ?namesake ?namesakeLabel ?genderLabel ?articleName
WHERE
{
  ?spacerock wdt:P138 ?namesake.
  ?namesake wdt:P31 wd:Q5.
  ?spacerock wdt:P31 wd:Q3863.
  ?spacerock wdt:P1457 ?magnitude.
  OPTIONAL {
      ?namesake wdt:P21 ?gender.
  }
  OPTIONAL {
      ?article schema:about ?namesake .
      ?article schema:inLanguage "en" .
      FILTER (SUBSTR(str(?article), 1, 25) = "https://en.wikipedia.org/")
  }

  BIND(SUBSTR(str(?article), 31) as ?articleName).
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
GROUP BY ?spacerock ?spacerockLabel ?namesake ?namesakeLabel ?genderLabel ?articleName
"""

edit_counts = pd.read_csv('edit_counts.csv', index_col=0)

def get_num_wiki_edits(page, reload_cached=False):
    if not reload_cached:
        try:
            return edit_counts.loc[page]['wikiEdits']
        except KeyError:
            pass
    print(f'Fetching missing edit count for {page}')
    url = f'https://xtools.wmflabs.org/api/page/articleinfo/en.wikipedia.org/{page}'
    r = requests.get(url, params = {'format': 'json'})
    return r.json()['revisions']


def query_wikidata():
    r = requests.get(URL, params = {'format': 'json', 'query': QUERY})
    data = r.json()
    with open('dataset.json', mode='w') as f:
        f.write(r.text)

    spacerocks = []
    for item in data['results']['bindings']:
        spacerocks.append({
            'spacerockLabel': item['spacerockLabel']['value'],
            'avgMagnitude': item['avgMagnitude']['value'],
            'namesake': item['namesake']['value'].replace('http://www.wikidata.org/entity/', ''),
            'namesakeLabel': item['namesakeLabel']['value'],
            'namesakeGender': item['genderLabel']['value']
                if 'genderLabel' in item else None,
            'articleName': item['articleName']['value']
                if 'articleName' in item else None,
        })
    df = pd.DataFrame(spacerocks)
    df = df.dropna()
    return df


if __name__ == '__main__':
    df = query_wikidata()
    df.to_csv('data.csv')
    # Remove duplicates to avoid querying multiple times for the same person
    # Otto Hahn is an example of a person with more than one asteroid named after them
    article_names = df['articleName'].drop_duplicates()
    new_edit_counts = pd.DataFrame({
        'wikiEdits': article_names.apply(get_num_wiki_edits),
    })
    new_edit_counts.index = article_names
    new_edit_counts.to_csv('edit_counts.csv')
