import json
import os
import sys
from datetime import datetime
import yfinance as yf

import pandas as pd
import requests
import io
# 核心自选保底池 (包含重要中概股和一些可能不在指数内的巨头)
BASE_WATCHLIST = [
    {"symbol": "BABA", "market": "US", "label": "阿里巴巴(美)"},
    {"symbol": "PDD", "market": "US", "label": "拼多多"},
    {"symbol": "JD", "market": "US", "label": "京东"},
    {"symbol": "NTES", "market": "US", "label": "网易(美)"},
    {"symbol": "BIDU", "market": "US", "label": "百度(美)"},
    {"symbol": "TCOM", "market": "US", "label": "携程"},
    {"symbol": "TSM", "market": "US", "label": "台积电"},
    {"symbol": "0700.HK", "market": "HK", "label": "腾讯控股"},
    {"symbol": "9988.HK", "market": "HK", "label": "阿里巴巴-W"},
    {"symbol": "3690.HK", "market": "HK", "label": "美团-W"},
    {"symbol": "1810.HK", "market": "HK", "label": "小米集团-W"},
    {"symbol": "1211.HK", "market": "HK", "label": "比亚迪股份"},
    {"symbol": "0941.HK", "market": "HK", "label": "中国移动"},
    {"symbol": "2318.HK", "market": "HK", "label": "中国平安"},
]

def get_dynamic_watchlist():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始从网络动态抓取各大核心指数成分股名单...")
    symbols_dict = {}
    
    # 1. 添加入保底池
    for item in BASE_WATCHLIST:
        symbols_dict[item["symbol"]] = item

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 2. 抓取标普 500 (S&P 500)
    try:
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        resp = requests.get(sp500_url, headers=headers)
        sp500_table = pd.read_html(io.StringIO(resp.text))[0]
        for _, row in sp500_table.iterrows():
            sym = str(row['Symbol']).replace('.', '-') # BRK.B -> BRK-B
            name = str(row['Security'])
            symbols_dict[sym] = {"symbol": sym, "market": "US", "label": name}
        print(f"✓ 成功抓取 S&P 500 成分股: {len(sp500_table)} 只")
    except Exception as e:
        print(f"✗ 抓取 S&P 500 失败: {e}")

    # 3. 抓取纳斯达克 100 (Nasdaq 100)
    try:
        ndx_url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        resp = requests.get(ndx_url, headers=headers)
        ndx_table = pd.read_html(io.StringIO(resp.text))[4]
        for _, row in ndx_table.iterrows():
            sym = str(row['Ticker'])
            name = str(row['Company'])
            symbols_dict[sym] = {"symbol": sym, "market": "US", "label": name}
        print(f"✓ 成功抓取 Nasdaq 100 成分股: {len(ndx_table)} 只")
    except Exception as e:
        print(f"✗ 抓取 Nasdaq 100 失败: {e}")

    # 4. 抓取恒生指数 (Hang Seng Index)
    try:
        hsi_url = 'https://en.wikipedia.org/wiki/Hang_Seng_Index'
        resp = requests.get(hsi_url, headers=headers)
        hsi_table = pd.read_html(io.StringIO(resp.text))[5]
        # Wikipedia 恒指表格结构可能有变化，通常是 Ticker 列
        if 'Ticker' in hsi_table.columns:
            for _, row in hsi_table.iterrows():
                sym = str(row['Ticker'])
                name = str(row['Company'])
                # 维基百科上恒指代码通常是纯数字如 700，需转为 0700.HK
                if sym.isdigit():
                    sym = sym.zfill(4) + ".HK"
                symbols_dict[sym] = {"symbol": sym, "market": "HK", "label": name}
            print(f"✓ 成功抓取恒生指数成分股")
    except Exception as e:
        print(f"✗ 抓取恒生指数失败: {e}")

    final_list = list(symbols_dict.values())
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 动态标的池构建完成，共去重后计 {len(final_list)} 只标的！")
    return final_list

def format_currency(val):
    if val is None:
        return "-"
    if val >= 1e12:
        return f"{val / 1e12:.2f}T"
    if val >= 1e9:
        return f"{val / 1e9:.2f}B"
    if val >= 1e6:
        return f"{val / 1e6:.2f}M"
    return f"{val:.2f}"

def fetch_and_calculate():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始获取港美股财务数据与计算市赚率...")
    results = []

    watchlist = get_dynamic_watchlist()
    for item in watchlist:
        symbol = item["symbol"]
        market = item["market"]
        label = item["label"]

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            name = info.get("shortName") or info.get("longName") or label
            currency = info.get("currency", "USD")
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            market_cap = info.get("marketCap")
            
            pe_ttm = info.get("trailingPE")
            pe_forward = info.get("forwardPE")
            roe_raw = info.get("returnOnEquity")  # yfinance 返回小数，如 0.25 代表 25%
            pb = info.get("priceToBook")
            # 使用更稳定的 trailingAnnualDividendYield，它总是返回标准小数 (例如 0.0033 代表 0.33%)
            dividend_yield_raw = info.get("trailingAnnualDividendYield")
            dividend_yield_pct = None
            if dividend_yield_raw is not None:
                dividend_yield_pct = round(dividend_yield_raw * 100, 2)

            # 计算市赚率 (PR = PE / (ROE * 100))
            # 当 ROE=20% (roe_raw=0.2), PE=15 时, PR = 15 / (0.2 * 100) = 15 / 20 = 0.75
            pr = None
            pr_level = "unknown"
            roe_pct = round(roe_raw * 100, 2) if roe_raw is not None else None

            if pe_ttm is not None and pe_ttm > 0 and roe_pct is not None and roe_pct > 0:
                pr = round(pe_ttm / roe_pct, 2)
                if pr < 1.0:
                    pr_level = "undervalued"    # < 1: 极具性价比/低估
                elif pr <= 2.0:
                    pr_level = "fair"           # 1~2: 合理区间
                else:
                    pr_level = "overvalued"     # > 2: 估值偏高
            elif roe_pct is not None and roe_pct <= 0:
                pr_level = "loss_roe"           # 净资产收益率为负/亏损
            elif pe_ttm is not None and pe_ttm <= 0:
                pr_level = "loss_pe"

            stock_data = {
                "symbol": symbol,
                "name": name,
                "label": label,
                "market": market,
                "currency": currency,
                "price": round(current_price, 2) if current_price else None,
                "market_cap": market_cap,
                "market_cap_str": format_currency(market_cap),
                "pe_ttm": round(pe_ttm, 2) if pe_ttm else None,
                "pe_forward": round(pe_forward, 2) if pe_forward else None,
                "roe": roe_pct,
                "pb": round(pb, 2) if pb else None,
                "dividend_yield": dividend_yield_pct,
                "pr": pr,
                "pr_level": pr_level,
            }
            results.append(stock_data)
            print(f"✓ 成功: {symbol:<10} | {label:<8} | PE: {str(stock_data['pe_ttm']):<6} | ROE: {str(stock_data['roe'])+'%':<7} | PR: {str(stock_data['pr']):<5} ({pr_level})")

        except Exception as e:
            print(f"✗ 失败: {symbol} - 错误信息: {e}")

    # 默认按市赚率从小到大排序（优质低估排在最前面，无 PR 数据的放最后）
    results.sort(key=lambda x: (x["pr"] is None, x["pr"] if x["pr"] is not None else float("inf")))

    output_payload = {
        "formula": "PR = PE / (ROE * 100)",
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S (UTC+8)"),
        "total_count": len(results),
        "data": results
    }

    # 保存到当前目录的 data.json
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 成功写入数据至: {output_path} (共 {len(results)} 只标的)")

if __name__ == "__main__":
    fetch_and_calculate()
