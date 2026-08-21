import json
import os
import sys
from datetime import datetime
import yfinance as yf

# 关注的港美股核心股票池（可随时根据个人需求增删）
WATCHLIST = [
    # ─── 美股核心标的 ───
    {"symbol": "AAPL", "market": "US", "label": "苹果"},
    {"symbol": "MSFT", "market": "US", "label": "微软"},
    {"symbol": "GOOGL", "market": "US", "label": "谷歌"},
    {"symbol": "AMZN", "market": "US", "label": "亚马逊"},
    {"symbol": "NVDA", "market": "US", "label": "英伟达"},
    {"symbol": "META", "market": "US", "label": "Meta"},
    {"symbol": "TSLA", "market": "US", "label": "特斯拉"},
    {"symbol": "BRK-B", "market": "US", "label": "伯克希尔B"},
    {"symbol": "BABA", "market": "US", "label": "阿里巴巴(美)"},
    {"symbol": "PDD", "market": "US", "label": "拼多多"},
    {"symbol": "KO", "market": "US", "label": "可口可乐"},
    {"symbol": "MCD", "market": "US", "label": "麦当劳"},

    # ─── 港股核心标的 (yfinance 中港股代码加 .HK 后缀) ───
    {"symbol": "0700.HK", "market": "HK", "label": "腾讯控股"},
    {"symbol": "9988.HK", "market": "HK", "label": "阿里巴巴(港)"},
    {"symbol": "3690.HK", "market": "HK", "label": "美团"},
    {"symbol": "1810.HK", "market": "HK", "label": "小米集团"},
    {"symbol": "0941.HK", "market": "HK", "label": "中国移动"},
    {"symbol": "1211.HK", "market": "HK", "label": "比亚迪股份"},
    {"symbol": "2318.HK", "market": "HK", "label": "中国平安"},
    {"symbol": "9999.HK", "market": "HK", "label": "网易"},
    {"symbol": "0388.HK", "market": "HK", "label": "香港交易所"},
    {"symbol": "1024.HK", "market": "HK", "label": "快手"},
]

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

    for item in WATCHLIST:
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
            dividend_yield = info.get("dividendYield")  # 如 0.015 代表 1.5%

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
                "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
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
