from dotenv import dotenv_values
import pandas as pd
from main import PPI
from components import urls
import os

# Secrets from github actions
ppi_user = os.getenv("PPI_USER")
ppi_password = os.getenv("PPI_PASS")

app = PPI(ppi_user, ppi_password)

ticker_list_info = app.get_tickers_list(
    instrument_type=app.instrument_types.CORPORATE,
    operation_type=app.operation_types.COMPRA,
    settlement=app.settlements.T1)

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

itemID_list = pd.DataFrame(ticker_list_info["payload"])["itemId"].to_list()

dfs_intraday = []
dfs_other_than_fft = []
for item in itemID_list:
    technical = app.get_technical_data_bonds(
        settlement=app.settlements.T1,
        item_id=item
        )
    ticker_history = app.get_intraday_data(item_id=item, settlement=app.settlements.T1)
    df_history = pd.DataFrame(ticker_history["payload"])
    # df_fft = pd.DataFrame(technical["payload"]["flujosDeFondosTeoricos"])
    other_than_fft_dict = flatten_dict({k: technical["payload"][k] for k in technical["payload"] if k != "flujosDeFondosTeoricos"})
    if other_than_fft_dict["id"] != 0 and other_than_fft_dict["ticker"]:
        # data_price = get_volume_last_price(df_history)
        other_than_fft_dict['moneda_exposiciones'] = str(other_than_fft_dict['moneda_exposiciones'])
        df_other_than_fft = pd.DataFrame([other_than_fft_dict])
        # df_other_than_fft["volume"] = data_price["volume"]
        # df_other_than_fft["last_price"] = data_price["last_price"]
        dfs_intraday.append(df_history)
        dfs_other_than_fft.append(df_other_than_fft)
        
df_intraday = pd.concat(dfs_intraday)
df_other_than_fft = pd.concat(dfs_other_than_fft)
new_df = df_other_than_fft[["id", "nombre", "ticker"]].merge(df_intraday, how="inner", left_on="id", right_on="item")

previous_df = pd.read_csv("../data/intraday_data.csv")
df = pd.concat([previous_df, new_df]).reset_index(drop=True)
df = df.drop_duplicates()

df.to_csv("../data/intraday_data.csv", index=False)