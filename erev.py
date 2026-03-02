import streamlit as st
import pandas as pd
import io

# הגדרות דף
st.set_page_config(page_title="מחשבון שעות ערב לסוקרים", page_icon="📅", layout="centered")

# עיצוב כותרת
st.title("📊 מחשבון שעות ערב לסוקרים")
st.markdown("---")

# העלאת קובץ
uploaded_file = st.file_uploader("📂 גררו לכאן את קובץ האקסל או לחצו לבחירה", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # לוגיקה מקורית שלך
        df = pd.read_excel(uploaded_file, header=8)
        df["תאריך"] = pd.to_datetime(df["תאריך"], errors="coerce")
        df["שעת התחלה"] = pd.to_datetime(df["שעת התחלה"], errors="coerce")
        df["שעת סיום"] = pd.to_datetime(df["שעת סיום"], errors="coerce")
        df["שורה ראשית"] = df["תאריך"].notna()
        df["תאריך ממולא"] = df["תאריך"].ffill()

        df_work = df[df["שורה ראשית"] == False].copy()
        df_work = df_work[
            df_work["תאריך"].notna() |
            df_work["מספר שלב"].notna() |
            df_work["שם שלב"].notna() |
            df_work["שעת התחלה"].notna() |
            df_work["שעת סיום"].notna()
        ].copy()

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
        daily_sum = df_work.groupby("תאריך")["שעות ערב"].sum()
        df_work["ערב מזכה"] = df_work.apply(lambda r: r["שעות ערב"] if daily_sum[r["תאריך"]] >= 3 else 0.0, axis=1)
        df_work["ערב לא מזכה"] = df_work["שעות ערב"] - df_work["ערב מזכה"]

        daily = df_work.groupby("תאריך")[["שעות ערב", "ערב מזכה", "ערב לא מזכה"]].sum()
        
        # תצוגה לסוקר
        st.subheader("📅 סיכום שעות יומי")
        
        # עיצוב טבלה יפה
        display_daily = daily.copy()
        display_daily.index = display_daily.index.strftime('%d/%m/%Y')
        st.table(display_daily.style.format("{:.2f}"))

        # חישוב חודשי
        total_evening = df_work["שעות ערב"].sum()
        total_work = df_work["משך"].sum()
        percent = (total_evening / total_work) if total_work > 0 else 0

        # כרטיסיית סיכום
        st.markdown("---")
        st.subheader("🏁 סיכום זכאות חודשית")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("סה\"כ שעות עבודה", f"{total_work:.2f}")
        col2.metric("סה\"כ שעות ערב", f"{total_evening:.2f}")
        col3.metric("אחוז שעות ערב", f"{percent*100:.1f}%")

        if percent >= 0.5:
            st.success("🎉 **מזל טוב! אתה זכאי לתוספת ערב החודש 🐱**")
            st.balloons()
        else:
            st.error("❌ **אינך זכאי לתוספת ערב החודש (פחות מ-50%)**")

    except Exception as e:
        st.error(f"אירעה שגיאה בעיבוד הקובץ: {e}")
