from fpdf import FPDF

# Clean version without emojis or special characters
text_clean = """
requirements.txt – TrendFollowing ATR Stops Strategy (1:3 RR, No Breakeven)

General Information
- Strategy Name: TRENDFOLLOW - ATR Stops 1:3 RR (No Breakeven)
- Type: Trend-following breakout with dynamic zones and stepped RSI
- Entry/Exit Logic: Based on SMI zones, stepped RSI crossovers, ATR-based stop loss, and fixed reward-risk ratio (1:3)
- No Breakeven, No Trailing Stops
- Platform Target: MQL5 (MetaTrader 5 Expert Advisor using CTrade class)
- HTF Logic: All indicators use values from higher timeframes

Inputs

Timeframe Settings
| Name       | Type             | Default     | Description                        |
|------------|------------------|-------------|------------------------------------|
| kkbTF      | ENUM_TIMEFRAMES  | PERIOD_D1   | Higher timeframe for kkb SMI       |
| metroTF    | ENUM_TIMEFRAMES  | PERIOD_D1   | Higher timeframe for Metro RSI     |

Indicator Periods
| Name         | Type   | Default | Description                    |
|--------------|--------|---------|--------------------------------|
| lengthK      | int    | 26      | %K period for SMI              |
| lengthD      | int    | 8       | %D (EMA smoothing) for SMI     |
| lengthEMA    | int    | 6       | EMA smoothing for SMI          |
| periodRSI    | int    | 32      | RSI period for Metro RSI       |
| stepSizeFast | float  | 12.0    | Step size for fast Metro RSI   |
| stepSizeSlow | float  | 21.0    | Step size for slow Metro RSI   |

Risk Management
| Name             | Type   | Default | Description                                |
|------------------|--------|---------|--------------------------------------------|
| atrLength        | int    | 14      | ATR period for SL calculation              |
| atrMultiplier    | float  | 2.0     | Multiplier for ATR-based Stop Loss         |
| riskRewardRatio  | float  | 3.0     | Take Profit multiplier relative to SL (1:3)|

Indicator Calculations

SMI (Stochastic Momentum Index) - From Higher Timeframe (kkbTF)
- SMI Formula:
    SMI = 200 × [EMA(EMA(relativeRange, lengthD), lengthD) / EMA(EMA(highestLowestRange, lengthD), lengthD)]
    where:
    - relativeRange = close - ((highestHigh + lowestLow) / 2)
    - highestLowestRange = highestHigh - lowestLow
- Zone Definitions:
    - inBuyZone: SMI < -40
    - inSellZone: SMI > 40

Metro RSI Stepped Filter (From metroTF)
- fastStep[i] = clamp(rsiHTF - stepSizeFast, rsiHTF + stepSizeFast, fastStep[i-1])
- slowStep[i] = clamp(rsiHTF - stepSizeSlow, rsiHTF + stepSizeSlow, slowStep[i-1])
- Cross Conditions:
    - fastCrossSlow = crossover(fastStep, slowStep)
    - slowCrossFast = crossunder(fastStep, slowStep)

Trading Logic

Entry Conditions
Long:
    - higherSMI < -40 AND higherSMI > higherSMI[1] AND fastStep > slowStep
    - OR fastStep crosses over slowStep

Short:
    - higherSMI > 40 AND higherSMI < higherSMI[1] AND fastStep < slowStep
    - OR fastStep crosses under slowStep

Exit Conditions
- Stop Loss = ATR(atrLength) × atrMultiplier
- Take Profit = StopLoss × riskRewardRatio

Long:
    SL = entry - stopLossDistance
    TP = entry + takeProfitDistance

Short:
    SL = entry + stopLossDistance
    TP = entry - takeProfitDistance

State Tracking
- entryPrice
- buySignalTriggered, sellSignalTriggered
- Reset when SMI leaves current zone

Miscellaneous
- No breakeven or trailing stop

--- END ---
"""
text_clean = text_clean.encode("ascii", "ignore").decode()

# Create PDF
pdf_clean = FPDF()
pdf_clean.add_page()
pdf_clean.set_auto_page_break(auto=True, margin=10)
pdf_clean.set_font("Arial", size=10)

for line in text_clean.split('\n'):
    pdf_clean.cell(0, 8, txt=line.strip(), ln=True)

pdf_clean_path = "trendfollow_requirements.pdf"
pdf_clean.output(pdf_clean_path)
