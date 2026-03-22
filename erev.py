import streamlit as st
import pandas as pd
import datetime

# הגדרות דף - תצוגה נקייה ומודרנית
st.set_page_config(page_title="מחשבון סוקרים משולב", page_icon="📊", layout="centered")

# --- פונקציה לחישוב מדרגות נסיעה ---
def calculate_km_payment(total_km):
    steps = [
        (250, 1.5),   # עד 250 ק"מ
        (250, 1.6),   # 250-500 ק"מ
        (250, 1.7),   # 500-750 ק"מ
        (250, 1.8),   # 750-1000 ק"מ
        (float('inf'), 1.9) # מעל 1000 ק"מ
    ]
    payment = 0
    remaining = total_km
    details = []
    for limit, rate in steps:
        if remaining <= 0: break
        km_in_step = min(remaining, limit)
        step_pay = km_in_step * rate
        payment += step_pay
        details.append({
            "מדרגת תשלום (₪)": f"{rate}",
            "ק\"מ בפועל": f"{km_in_step:.1f}",
            "תשלום במדרגה": f"₪ {step_pay:,.1f}"
        })
        remaining -= km_in_step
    return payment, details

# --- סרגל צד לניווט ---
st.sidebar.title("🛠️ כלי עזר לסוקר")
st.sidebar.markdown("---")
page = st.sidebar.radio("בחר מחשבון:", ["⏰ מחשבון שעות ערב", "🚗 מחשבון נסיעות"])
st.sidebar.markdown("---")
st.sidebar.info("פותח עבור צוות הסוקרים 🐱")

# --- דף 1: מחשבון שעות ערב ---
if page == "⏰ מחשבון שעות ערב":
    st.title("🕒 מחשבון שעות ערב (אקסל)")
    st.write("העלו את קובץ האקסל המקורי כדי לחשב זכאות לתוספת ערב.")
    uploaded_file = st.file_uploader("בחר קובץ אקסל (.xlsx)", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, header=8)
            df["תאריך"] = pd.to_datetime(df["תאריך"], errors="coerce")
            df["שעת התחלה"] = pd.to_datetime(df["שעת התחלה"], errors="coerce")
            df["שעת סיום"] = pd.to_datetime(df["שעת סיום"], errors="coerce")
            df["שורה ראשית"] = df["תאריך"].notna()
            df["תאריך ממולא"] = df["תאריך"].ffill()

            df_work = df[df["שורה ראשית"] == False].copy()
            df_work = df_work[df_work["תאריך ממולא"].notna() & df_work["שעת התחלה"].notna()].copy()
            df_work["תאריך"] = df_work["תאריך ממולא"]

            non_evening_stages = {110, 130, 132}
            df_work["משך"] = (df_work["שעת סיום"] - df_work["שעת התחלה"]).dt.total_seconds() / 3600

            def evening_hours(row):
                start, end, stage = row["שעת התחלה"], row["שעת סיום"], row["מספר שלב"]
                if stage in non_evening_stages or pd.isnull(start) or pd.isnull(end): return 0.0
                cutoff = start.replace(hour=14, minute=0, second=0)
                if end <= cutoff: return 0.0
                return (end - max(start, cutoff)).total_seconds() / 3600

            df_work["שעות ערב"] = df_work.apply(evening_hours, axis=1)
            daily = df_work.groupby("תאריך")["שעות ערב"].sum()
            total_ev = df_work["שעות ערב"].sum()
            total_work = df_work["משך"].sum()
            percent = (total_ev / total_work) if total_work > 0 else 0

            st.success("✅ החישוב בוצע בהצלחה")
            col1, col2, col3 = st.columns(3)
            col1.metric("סה\"כ שעות", f"{total_work:.2f}")
            col2.metric("שעות ערב", f"{total_ev:.2f}")
            col3.metric("אחוז ערב", f"{percent*100:.1f}%")

            st.markdown("### 📅 פירוט יומי")
            daily_df = pd.DataFrame(daily)
            daily_df.index = daily_df.index.strftime('%d/%m/%Y')
            st.table(daily_df.style.format("{:.2f}"))

            if percent >= 0.5:
                st.balloons()
                st.success("🐱 **זכאי לתוספת ערב החודש!**")
            else:
                st.warning("✖ **לא הגעת ל-50% שעות ערב**")
        except Exception as e:
            st.error(f"שגיאה בעיבוד הקובץ: {e}")

# --- דף 2: מחשבון נסיעות ---
elif page == "🚗 מחשבון נסיעות":
    st.title("🚗 מחשבון החזר נסיעות")
    st.write("הזן את סה\"כ הקילומטרים שביצעת החודש.")

    km_input = st.number_input("סה\"כ קילומטרים (ק\"מ):", min_value=0.0, step=1.0, value=0.0)

    if km_input > 0:
        total_pay, details = calculate_km_payment(km_input)
        
        # תצוגה נקייה של הסכום לתשלום
        st.subheader(f"💰 סה\"כ לתשלום: ₪ {total_pay:,.2f}")
        st.info(f"החישוב בוצע עבור {km_input} קילומטרים.")
        
        st.write("#### 📋 פירוט החישוב לפי מדרגות:")
        st.table(pd.DataFrame(details))
    else:
        st.info("הזן כמות קילומטרים בשדה למעלה כדי לראות את החישוב.")

    with st.expander("ℹ️ הסבר על מדרגות התשלום"):
        st.write("""
        התשלום מחושב באופן פרוגרסיבי:
        - 1.5 ₪ לק"מ עבור 250 הק"מ הראשונים.
        - 1.6 ₪ לק"מ עבור המדרגה של 250-500 ק"מ.
        - 1.7 ₪ לק"מ עבור המדרגה של 500-750 ק"מ.
        - 1.8 ₪ לק"מ עבור המדרגה של 750-1000 ק"מ.
        - 1.9 ₪ לק"מ עבור כל קילומטר מעל 1000.
        """)
