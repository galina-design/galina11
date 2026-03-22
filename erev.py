import streamlit as st
import pandas as pd
import io

# הגדרות דף - עיצוב מודרני
st.set_page_config(page_title="מחשבון סוקרים משולב", page_icon="📊", layout="centered")

# --- פונקציות עזר לנסיעות ---
def calculate_km_payment(total_km):
    # מדרגות לפי הטבלה ששלחת
    steps = [
        (250, 1.5),   # מדרגה 1: 0-250
        (250, 1.6),   # מדרגה 2: 250-500
        (250, 1.7),   # מדרגה 3: 500-750
        (250, 1.8),   # מדרגה 4: 750-1000
        (float('inf'), 1.9) # מדרגה 5: מעל 1000
    ]
    
    payment = 0
    remaining = total_km
    details = []

    for limit, rate in steps:
        if remaining <= 0: break
        km_in_step = min(remaining, limit)
        step_pay = km_in_step * rate
        payment += step_pay
        details.append({"מדרגת תשלום (₪)": f"{rate}", "ק\"מ בפועל": f"{km_in_step:.1f}", "תשלום במדרגה": f"₪ {step_pay:,.1f}"})
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
            # לוגיקה מקורית (עיבוד אקסל)
            df = pd.read_excel(uploaded_file, header=8)
            df["תאריך"] = pd.to_datetime(df["תאריך"], errors="coerce")
            df["שעת התחלה"] = pd.to_datetime(df["שעת התחלה"], errors="coerce")
            df["שעת סיום"] = pd.to_datetime(df["שעת סיום"], errors="coerce")
            df["תאריך ממולא"] = df["תאריך"].ffill()

            # סינון שורות עבודה (שורות המשך)
            df_work = df[df["תאריך"].isna()].copy() # שורות המשך ללא תאריך במקור
            df_work = df_work[df_work["שעת התחלה"].notna()].copy()
            df_work["תאריך"] = df["תאריך ממולא"][df_work.index]

            non_evening_stages = {110, 130, 132}
            df_work["משך"] = (df_work["שעת סיום"] - df_work["שעת התחלה"]).dt.total_seconds() / 3600

            def evening_hours(row):
                start, end, stage = row["שעת התחלה"], row["שעת סיום"], row["מספר שלב"]
                if stage in non_evening_stages or pd.isnull(start) or pd.isnull(end): return 0.0
                cutoff = start.replace(hour=14, minute=0, second=0)
                if end <= cutoff: return 0.0
                return (end - max(start, cutoff)).total_seconds() / 3600

            df_work["שעות ערב"] = df_work.apply(evening_hours, axis=1)
            
            # חישוב יומי
            daily = df_work.groupby("תאריך")["שעות ערב"].sum()
            total_ev = df_work["שעות ערב"].sum()
            total_work = df_work["משך"].sum()
            percent = (total_ev / total_work) if total_work > 0 else 0

            # הצגת תוצאות
            st.success("✅ הקובץ עובד בהצלחה")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("סה\"כ שעות", f"{total_work:.2f}")
            col2.metric("שעות ערב", f"{total_ev:.2f}")
            col3.metric("אחוז ערב", f"{percent*100:.1f}%")

            st.markdown("### 📅 פירוט יומי")
            daily_df = pd.DataFrame(daily)
            daily_df.columns = ["שעות ערב"]
            daily_df.index = daily_df.index.strftime('%d/%m/%Y')
            st.table(daily_df.style.format("{:.2f}"))

            if percent >= 0.5:
                st.balloons()
                st.success("🐱 **אתה זכאי לתוספת ערב החודש!**")
            else:
                st.error("✖ **אינך זכאי לתוספת ערב החודש**")

        except Exception as e:
            st.error(f"שגיאה בעיבוד הקובץ: {e}")

# --- דף 2: מחשבון נסיעות ---
elif page == "🚗 מחשבון נסיעות":
    st.title("🚗 מחשבון החזר נסיעות")
    st.write("הזן את סה\"כ הקילומטרים שביצעת החודש לקבלת סכום ההחזר.")

    km_input = st.number_input("סה\"כ קילומטרים (ק\"מ):", min_value=0.0, step=1.0, value=0.0)

    if km_input > 0:
        total_pay, details = calculate_km_payment(km_input)
        
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; border-right: 5px solid #1a73e8;">
            <h2 style="margin:0; color:#1a73e8;">סה\"כ לתשלום: ₪ {total_pay:,.2f}</h2>
        </div>
        """, unsafe_content_type=True)

        st.write("#### 📋 פירוט החישוב לפי מדרגות:")
        st.table(pd.DataFrame(details))
    else:
        st.info("הזן כמות קילומטרים כדי לראות את החישוב.")

    with st.expander("ℹ️ הסבר על מדרגות התשלום"):
        st.write("""
        התשלום מחושב באופן פרוגרסיבי:
        - 1.5 ₪ לק"מ עבור 250 הק"מ הראשונים.
        - 1.6 ₪ לק"מ עבור המדרגה של 250-500 ק"מ.
        - 1.7 ₪ לק"מ עבור המדרגה של 500-750 ק"מ.
        - 1.8 ₪ לק"מ עבור המדרגה של 750-1000 ק"מ.
        - 1.9 ₪ לק"מ עבור כל קילומטר מעל 1000.
        """)
