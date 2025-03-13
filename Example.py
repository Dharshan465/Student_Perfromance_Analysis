import streamlit as st
import pandas as pd
import altair as alt
st.set_page_config(page_title="Student Performance Analysis", layout="wide")

# Department abbreviations
DEPT_ABBREVIATIONS = {
    "AEROSPACE ENGINEERING": "AERO",
    "AUTOMOBILE ENGINEERING": "AUTO",
    "ELECTRONICS ENGINEERING": "ECE",
    "INFORMATION TECHNOLOGY": "IT",
    "INSTRUMENTATION ENGINEERING": "E&I",
    "PRODUCTION TECHNOLOGY": "PT",
    "RUBBER AND PLASTICS TECHNOLOGY": "RPT"
}

# Department prefixes
DEPT_PREFIX = {
    "Aerospace": "AE", "Automobile": "AU", "Electronics Comm": "EC", "Artificial Intelligence": "AZ",
    "Information Tech": "IT", "Inst Eng": "EI", "Mech": "ME", "Production": "PR",
    "Robotics": "RO", "Rubber and Plastics": "RP"
}

# Set page layout (header and footer styling)
st.markdown("""
    <style>
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            background-color: #99e6ff;
            border-bottom: 2px solid #ddd;
            width: 100%;
        }
        .header-title {
            font-size: 34px;
            font-weight: bold;
            color: #333;
            text-align: center;
            flex-grow: 1;
        }
        .footer-container {
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: #f5f5f5;
            text-align: center;
            padding: 8px;
            font-size: 14px;
            border-top: 2px solid #ddd;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-container">
        <div class="header-title">MADRAS INSTITUTE OF TECHNOLOGY</div>
    </div>
""", unsafe_allow_html=True)

# Load Data with Error Handling
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, sheet_name="UG")
        required_cols = ["DEPNAME", "BRNAME", "SEM", "REGNO", "SUBCODE", "SUBTYPE", "SESMARK", "ESEM", "TOTMARK", "GRADE"]
        if not all(col in df.columns for col in required_cols):
            st.error("Excel file is missing required columns!")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# Pass/Fail Logic
def determine_pass_fail(df):
    df["Pass"] = df["GRADE"] != "U"
    student_pass_fail = df.groupby("REGNO")["Pass"].all().reset_index()
    student_pass_fail["Status"] = student_pass_fail["Pass"].map({True: "Pass", False: "Fail"})
    return student_pass_fail

# Grade Distribution per Subject
def grade_distribution_per_subject(df):
    grade_order = ["O", "A+", "A", "B+", "B", "C", "U"]
    subjects = df["SUBCODE"].unique()
    all_combinations = pd.MultiIndex.from_product([subjects, grade_order], names=["SUBCODE", "GRADE"])
    subject_grade_counts = df.groupby(["SUBCODE", "GRADE"]).size().reindex(all_combinations, fill_value=0).reset_index(name="Count")
    return subject_grade_counts

# Subjects Failed per Student
def subjects_failed(df):
    fail_counts = df[df["GRADE"] == "U"].groupby("REGNO")["SUBCODE"].count().value_counts().reset_index()
    fail_counts.columns = ["Subjects Failed", "Student Count"]
    return fail_counts

# Average Marks per Subject Calculation
def avg_marks_per_subject(df):
    df[["SESMARK", "ESEM", "TOTMARK"]] = df[["SESMARK", "ESEM", "TOTMARK"]].apply(pd.to_numeric, errors="coerce")
    subject_avg = df.groupby("SUBCODE").agg({
        "SESMARK": "mean",
        "ESEM": "mean",
        "TOTMARK": "mean"
    }).reset_index()
    subject_avg.columns = ["SUBJECT CODE", "INTERNAL", "EXTERNAL", "TOTAL"]
    return subject_avg

# Subject-wise Pass/Fail Count
def subject_wise_pass_fail(df):
    df["Pass"] = df["GRADE"] != "U"
    subject_pass_fail = df.groupby(["SUBCODE", "Pass"]).size().unstack(fill_value=0).reset_index()
    subject_pass_fail.columns = ["SUBJECT CODE", "Fail", "Pass"]
    return subject_pass_fail

# Chart: Pass/Fail Count (Pie Chart)
def pass_fail_chart(df):
    pass_fail_counts = df["Status"].value_counts().reset_index()
    pass_fail_counts.columns = ["Status", "Count"]
    pass_fail_counts = pass_fail_counts.set_index("Status").reindex(["Pass", "Fail"], fill_value=0).reset_index()
    total = pass_fail_counts["Count"].sum()
    pass_fail_counts["Percentage"] = pass_fail_counts["Count"] / total * 100

    base = alt.Chart(pass_fail_counts).encode(
        theta=alt.Theta("Count:Q", stack=True),
        color=alt.Color("Status:N", scale=alt.Scale(domain=["Pass", "Fail"], range=["#5cf074", "#fa4931"]), legend=alt.Legend(title="Status", labelFontSize=16, titleFontSize=18)),
        tooltip=["Status", "Count", alt.Tooltip("Percentage:Q", title="Percentage", format=".1f")]
    ).properties(
        title=alt.TitleParams(f"Pass/Fail Count (Total: {total})", fontSize=20, fontWeight="bold"),
        width=400,
        height=400
    )

    pie = base.mark_arc(outerRadius=120)
    text = base.mark_text(radius=140, size=16, fontWeight="bold").encode(
        text="Count:Q"
    )

    return pie + text

# Chart: Department-wise Pass/Fail
def plot_department_wise_chart(department_pass_fail, selected_semester):
    department_df = department_pass_fail.reset_index().melt(id_vars="DEPNAME_SHORT", var_name="Result", value_name="Count")
    color_scale = alt.Scale(domain=["Pass", "Fail"], range=["green", "red"])
    chart = alt.Chart(department_df).mark_bar(width=30).encode(
        x=alt.X("DEPNAME_SHORT:N", title="Departments", axis=alt.Axis(labelAngle=-45, labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
        y=alt.Y("Count:Q", title="Student Count", axis=alt.Axis(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
        color=alt.Color("Result:N", scale=color_scale, legend=alt.Legend(title="Result", labelFontSize=16, titleFontSize=18)),
        xOffset=alt.X("Result:N", sort=["Pass", "Fail"])
    ).properties(title=alt.TitleParams(f"Department-wise Pass/Fail Count ({selected_semester})", fontSize=20, fontWeight="bold"))
    text = chart.mark_text(align="center", baseline="bottom", dy=-5, fontSize=16, fontWeight="bold", color="black").encode(text="Count:Q")
    return chart + text

# Chart: Semester-wise Arrear Count Distribution
def subjects_failed_chart(df):
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Subjects Failed:N", title="No of Arrears", axis=alt.Axis(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
        y=alt.Y("Student Count:Q", title="Number of Students", axis=alt.Axis(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
        color=alt.Color("Subjects Failed:N", scale=alt.Scale(scheme="category20")),
        tooltip=["Subjects Failed", "Student Count"]
    ).properties(title=alt.TitleParams("Semester-wise Arrear Count Distribution", fontSize=20, fontWeight="bold"))
    text = chart.mark_text(dy=-10, fontSize=16, fontWeight="bold").encode(text="Student Count")
    return chart + text

# Chart: Subject-wise Pass/Fail (Multiple Charts if > 5 subjects)
def plot_subject_wise_pass_fail(subject_pass_fail, title_prefix):
    subject_df = subject_pass_fail.reset_index().melt(id_vars="SUBJECT CODE", var_name="Result", value_name="Count")
    color_scale = alt.Scale(domain=["Pass", "Fail"], range=["#5cf074", "#fa4931"])
    
    subjects = subject_pass_fail["SUBJECT CODE"].tolist()
    subjects_per_chart = 5
    num_charts = (len(subjects) + subjects_per_chart - 1) // subjects_per_chart

    for i in range(num_charts):
        start_idx = i * subjects_per_chart
        end_idx = min((i + 1) * subjects_per_chart, len(subjects))
        subset_subjects = subjects[start_idx:end_idx]
        subset_data = subject_df[subject_df["SUBJECT CODE"].isin(subset_subjects)]

        chart = alt.Chart(subset_data).mark_bar(width=40).encode(
            x=alt.X("SUBJECT CODE:N", title="Subjects", axis=alt.Axis(labelAngle=-45, labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
            y=alt.Y("Count:Q", title="Student Count", axis=alt.Axis(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
            color=alt.Color("Result:N", scale=color_scale, legend=alt.Legend(title="Result", labelFontSize=16, titleFontSize=18)),
            xOffset=alt.X("Result:N", sort=["Pass", "Fail"])
        ).properties(title=alt.TitleParams(f"{title_prefix} - Part {i+1}", fontSize=20, fontWeight="bold"))

        text = chart.mark_text(align="center", baseline="bottom", dy=-5, fontSize=16, fontWeight="bold", color="black").encode(text="Count:Q")
        st.altair_chart(chart + text, use_container_width=True)

# Chart: Average Marks per Subject (Multiple Charts if > 5 subjects)
def plot_avg_marks_per_subject(subject_avg, title_prefix):
    subject_avg_melted = subject_avg.melt(id_vars="SUBJECT CODE", var_name="Category", value_name="Average Marks")
    subject_avg_melted["Average Marks"] = subject_avg_melted["Average Marks"].round(2)
    color_palette = alt.Scale(domain=["INTERNAL", "EXTERNAL", "TOTAL"], range=["#4682B4", "#8B0000", "#228B22"])
    
    subjects = subject_avg["SUBJECT CODE"].tolist()
    subjects_per_chart = 5
    num_charts = (len(subjects) + subjects_per_chart - 1) // subjects_per_chart

    for i in range(num_charts):
        start_idx = i * subjects_per_chart
        end_idx = min((i + 1) * subjects_per_chart, len(subjects))
        subset_subjects = subjects[start_idx:end_idx]
        subset_data = subject_avg_melted[subject_avg_melted["SUBJECT CODE"].isin(subset_subjects)]

        chart = alt.Chart(subset_data).mark_bar(width=30).encode(
            x=alt.X("SUBJECT CODE:N", title="Subjects", axis=alt.Axis(labelAngle=-45, labelFontSize=16, titleFontSize=18, labelFontWeight="bold")),
            y=alt.Y("Average Marks:Q", title="Average Marks", axis=alt.Axis(labelFontSize=16, titleFontSize=18, labelFontWeight="bold")),
            color=alt.Color("Category:N", scale=color_palette, legend=alt.Legend(title="Category", labelFontSize=16, titleFontSize=18)),
            xOffset=alt.X("Category:N", sort=["INTERNAL", "EXTERNAL", "TOTAL"])
        ).properties(title=alt.TitleParams(f"{title_prefix} - Part {i+1}", fontSize=18, fontWeight="bold"))

        text = chart.mark_text(align="center", baseline="bottom", dy=-5, fontSize=12, fontWeight="bold", color="black").encode(
            text=alt.Text("Average Marks:Q", format=".2f")
        )
        st.altair_chart(chart + text, use_container_width=True)

def plot_grade_distribution_per_subject(subject_grade_counts, title_prefix):
    grade_order = ["O", "A+", "A", "B+", "B", "C", "U"]
    grade_color_scale = alt.Scale(
        domain=grade_order,
        range=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"]
    )
    
    subjects = subject_grade_counts["SUBCODE"].unique()
    subjects_per_chart = 5  # Maximum of 5 subjects per chart
    num_charts = (len(subjects) + subjects_per_chart - 1) // subjects_per_chart

    st.markdown("""
        <style>
        .center-chart {
            display: flex;
            justify-content: center;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    for i in range(num_charts):
        start_idx = i * subjects_per_chart
        end_idx = min((i + 1) * subjects_per_chart, len(subjects))
        subset_subjects = subjects[start_idx:end_idx]
        subset_data = subject_grade_counts[subject_grade_counts["SUBCODE"].isin(subset_subjects)]

        # Base chart with bars, no x-axis title
        bars = alt.Chart(subset_data).mark_bar(size=15).encode(
            x=alt.X("GRADE:N", title=None, sort=grade_order, axis=alt.Axis(labelFontSize=16, labelFontWeight="bold")),
            y=alt.Y("Count:Q", title="Number of Students", axis=alt.Axis(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold")),
            color=alt.Color("GRADE:N", scale=grade_color_scale, legend=alt.Legend(title="Grade", labelFontSize=16, titleFontSize=18))
        )

        # Text layer for counts, no x-axis title
        text = alt.Chart(subset_data).mark_text(align="center", baseline="bottom", dy=-5, fontSize=14, fontWeight="bold", color="black").encode(
            x=alt.X("GRADE:N", sort=grade_order),
            y=alt.Y("Count:Q"),
            text=alt.condition(alt.datum.Count > 0, alt.Text("Count:Q"), alt.value(""))
        )

        # Layer the bars and text before faceting
        layered_chart = alt.layer(bars, text).properties(
            height=400
        )

        # Apply faceting to the layered chart
        final_chart = layered_chart.facet(
            column=alt.Column("SUBCODE:N", title="Subject", header=alt.Header(labelFontSize=16, labelFontWeight="bold", titleFontSize=18, titleFontWeight="bold"))
        ).properties(
            title=alt.TitleParams(f"{title_prefix} - Part {i+1}", fontSize=20, fontWeight="bold")
        ).configure_facet(
            spacing=20  # Spacing between facets
        )

        # Center the chart and add a custom "Grade" title below via Streamlit
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="center-chart">', unsafe_allow_html=True)
            st.altair_chart(final_chart, use_container_width=True)
            st.markdown('<div style="text-align: center; font-size: 18px; font-weight: bold;">Grade</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# Department-wise Pass/Fail Count
def department_wise_pass_fail(df):
    df["Pass"] = df["GRADE"] != "U"
    student_pass_fail = df.groupby("REGNO")["Pass"].all().reset_index()
    student_pass_fail["Status"] = student_pass_fail["Pass"].map({True: "Pass", False: "Fail"})
    df_unique = df[["REGNO", "DEPNAME"]].drop_duplicates()
    student_pass_fail = student_pass_fail.merge(df_unique, on="REGNO", how="left")
    student_pass_fail["DEPNAME_SHORT"] = student_pass_fail["DEPNAME"].map(DEPT_ABBREVIATIONS)
    department_pass_fail = student_pass_fail.groupby(["DEPNAME_SHORT", "Status"]).size().unstack(fill_value=0)
    return department_pass_fail.reindex(columns=["Pass", "Fail"], fill_value=0)

# Streamlit UI
st.title("Student Performance Analysis")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
    if df is None:
        st.stop()

    columns_to_keep = ["DEPNAME", "BRNAME", "SEM", "REGNO", "SUBCODE", "SUBTYPE", "SESMARK", "ESEM", "TOTMARK", "GRADE"]
    df = df[columns_to_keep].copy()

    department_options = ["Overall", "Others (Open Elective)"] + sorted(df["DEPNAME"].unique())
    selected_department = st.selectbox("Select Department", department_options)

    if selected_department not in ["Overall", "Others (Open Elective)"]:
        selected_branch = st.selectbox("Select Branch", ["All"] + sorted(df[df["DEPNAME"] == selected_department]["BRNAME"].unique()))
    else:
        selected_branch = "All"

    selected_semester = st.selectbox("Select Semester", ["Overall", "5", "7"])

    filtered_df = df.copy()
    if selected_department == "Others (Open Elective)":
        all_prefixes = tuple(DEPT_PREFIX.values())
        df_others = df[~df["SUBCODE"].str.startswith(all_prefixes)].copy()
        extra_subjects = {
            "Aeronautical": ['HM5503', 'EC5797', 'PR5791', 'EC5796', 'RP5591', 'EI5791', 'AU5791', 'ME5796', 'IT5794'],
            "Automobile": ['GE5552', 'IT5794', 'GE5451', 'ITM503', 'ITM505', 'EC5796', 'EC5797', 'PR5791', 'RP5591', 'AE5795', 'ME5796'],
            "ECE": ['HU5176', 'IT5794', 'MG5451', 'PH5202', 'EI5791', 'HU5172', 'HU5171', 'ME5796', 'HU5173', 'PR5791', 'HU5177', 'AU5791', 'AE5795', 'HU5174', 'RP5591'],
            "AI": ['HU5173', 'HU5176', 'HU5171', 'HU5172', 'HU5177'],
            "IT": ['HU5174', 'HU5177', 'HU5172', 'HU5173', 'HU5176', 'HU5171', 'EC5797', 'EC5796', 'AE5795', 'AU5791', 'EI5791', 'ME5796', 'PR5791', 'RP5591'],
            "EI": ['HM5501', 'ME5796', 'RP5591', 'EC5796', 'EC5797', 'IT5794', 'PR5791', 'AE5795'],
            "Mech": ['ITM503', 'ITM505', 'AU5791', 'AE5795', 'GE5152', 'MA5252'],
            "Production": ['GE5551', 'HS5151', 'ITM503', 'ITM505', 'EEM504', 'EEM503', 'EI5791', 'EC5796', 'IT5794', 'AE5795'],
            "Robo": ['EE5402', 'ITM503', 'ITM505', 'MA5158'],
            "Rubber": ['HU5171', 'HU5176', 'HU5172', 'ITM503', 'ITM505', 'HU5177', 'HU5174', 'GE5451', 'ME5796', 'EC5797', 'AE5795', 'AU5791', 'EC5796']
        }
        subject_list = sorted(df_others["SUBCODE"].unique())
        for subjects in extra_subjects.values():
            subject_list.extend(subjects)
        subject_list = sorted(set(subject_list))
        df_extra = df[df["SUBCODE"].isin(subject_list)]
        filtered_df = pd.concat([df_others, df_extra]).drop_duplicates()
    elif selected_department != "Overall":
        filtered_df = df[df["DEPNAME"] == selected_department].copy()
        if selected_branch != "All":
            filtered_df = filtered_df[filtered_df["BRNAME"] == selected_branch]

    if selected_semester != "Overall":
        filtered_df = filtered_df[filtered_df["SEM"] == int(selected_semester)]

    if filtered_df.empty:
        st.warning(f"No data available for {selected_department} - {selected_branch} in Semester {selected_semester}")
    else:
        pass_fail_df = determine_pass_fail(filtered_df)
        subjects_failed_df = subjects_failed(filtered_df)
        department_pass_fail = department_wise_pass_fail(filtered_df)
        subject_pass_fail = subject_wise_pass_fail(filtered_df)
        subject_avg = avg_marks_per_subject(filtered_df)
        subject_grade_counts = grade_distribution_per_subject(filtered_df)

        if selected_department == "Overall":
            st.subheader("1. Pass/Fail Count")
            st.altair_chart(pass_fail_chart(pass_fail_df), use_container_width=True)

            st.subheader("2. Department-wise Pass/Fail Count")
            st.altair_chart(plot_department_wise_chart(department_pass_fail, selected_semester), use_container_width=True)

            st.subheader("3. Semester-wise Arrear Count Distribution")
            st.altair_chart(subjects_failed_chart(subjects_failed_df), use_container_width=True)

        elif selected_department == "Others (Open Elective)":
            st.subheader("1. Subject-wise Pass/Fail Count")
            plot_subject_wise_pass_fail(subject_pass_fail, "Subject-wise Pass/Fail Count")

            st.subheader("2. Average Marks per Subject")
            plot_avg_marks_per_subject(subject_avg, "Average Marks per Subject")

            st.subheader("3. Grade Distribution per Subject")
            plot_grade_distribution_per_subject(subject_grade_counts, "Grade Distribution per Subject")

        else:  # Specific Department
            st.subheader("1. Pass/Fail Count")
            st.altair_chart(pass_fail_chart(pass_fail_df), use_container_width=True)

            st.subheader("2. Subject-wise Pass/Fail Count")
            plot_subject_wise_pass_fail(subject_pass_fail, "Subject-wise Pass/Fail Count")

            st.subheader("3. Average Marks per Subject")
            plot_avg_marks_per_subject(subject_avg, "Average Marks per Subject")

            st.subheader("4. Grade Distribution per Subject")
            plot_grade_distribution_per_subject(subject_grade_counts, "Grade Distribution per Subject")

            st.subheader("5. Semester-wise Arrear Count Distribution")
            st.altair_chart(subjects_failed_chart(subjects_failed_df), use_container_width=True)

# Display Footer
st.markdown("""
    <div class="footer-container">
        Dharshan S | 2021506018 | dharshans465@gmail.com
    </div>
""", unsafe_allow_html=True)
