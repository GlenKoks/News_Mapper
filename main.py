import utils
from tabulate import tabulate
from tqdm import tqdm
import pandas as pd
import geo
import numpy as np

tqdm.pandas(desc="Extracting geo data")

path = 'Data/Geo_Data.csv'
df = pd.read_csv(path)
df = df.head(1000)

print(tabulate(df.head(1000), headers='keys', tablefmt='psql'))

# df['shows'] = np.random.randint(1000, 100000, size=len(df))
# df['ent'] = df['publication_title_name'].progress_apply( utils.extract_entities_natasha)
#
# entities_df = pd.json_normalize(df['ent'])
# df = pd.concat([df, entities_df], axis=1)
#
#
# df['country'] = df['locations'].apply(
#     lambda x: utils.safe_extract_countries(x, geo.lemma_to_country))
#
# # df.to_csv('Data/Geo_v2.csv', index=False)
# print(tabulate(df.head(100), headers='keys', tablefmt='psql'))


