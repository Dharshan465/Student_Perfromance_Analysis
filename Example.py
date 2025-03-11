import streamlit as st
import pandas as pd
import altair as alt
import streamlit as st
import base64
st.set_page_config(layout="wide")

# Set page layout (only for header and footer styling)
st.markdown("""
    <style>
        /* Header */
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            background-color: #f5f5f5;
            border-bottom: 2px solid #ddd;
            width: 100%;
        }
        .header-logo {
            height: 50px;
        }
        .header-title {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            text-align: center;
            flex-grow: 1;
        }

        /* Footer */
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

# Function to encode images as Base64 for inline display
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Paths to images (update these paths)
mit_logo_path = "mit_logo.png"
anna_logo_path = "anna_logo_grey.png"

# Convert images to Base64
mit_logo_base64 = encode_image(mit_logo_path)
anna_logo_base64 = encode_image(anna_logo_path)

# Display Header
st.markdown(f"""
    <div class="header-container">
        <img class="header-logo" src="data:image/png;base64,{mit_logo_base64}" alt="MIT Logo">
        <div class="header-title">MADRAS INSTITUTE OF TECHNOLOGY</div>
        <img class="header-logo" src="data:image/png;base64,{anna_logo_base64}" alt="Anna University Logo">
    </div>
""", unsafe_allow_html=True)


# Load Data
@st.cache_data
def load_data(uploaded_file):
    df = pd.read_excel(uploaded_file, sheet_name="UG") 
    return df

# Pass/Fail Logic
def determine_pass_fail(df):
    df["Pass"] = df["GRADE"] != "U"
    student_pass_fail = df.groupby("REGNO")["Pass"].all().reset_index()
    student_pass_fail["Status"] = student_pass_fail["Pass"].map({True: "Pass", False: "Fail"})
    return student_pass_fail

# Fail Categories
# Fail Categories
def categorize_failures(df):
    fail_df = df[df["GRADE"] == "U"].copy()

    # Ensure ESEM is treated as a string (to avoid NaN issues)
    fail_df["ESEM"] = fail_df["ESEM"].astype(str).str.strip().str.upper()

    # Assign fail categories directly based on ESEM values
    fail_df["Fail Type"] = fail_df["ESEM"].map({
        "P": "Prevention",
        "M": "Malpractice",
        "A": "Absent"
    }).fillna("Attempted")  # Default to "Attempted" if not P, M, or A

    return fail_df



# Grade Distribution
def grade_distribution(df):
    grade_order = ["O", "A+", "A", "B+", "B", "C", "U"]  # Ensuring correct order
    grade_dist = df.groupby("GRADE")["REGNO"].nunique().reset_index().rename(columns={"REGNO": "Count"})
    grade_dist["GRADE"] = pd.Categorical(grade_dist["GRADE"], categories=grade_order, ordered=True)
    return grade_dist.sort_values("GRADE")

# Subjects Failed per Student
def subjects_failed(df):
    fail_counts = df[df["GRADE"] == "U"].groupby("REGNO")["SUBCODE"].count().value_counts().reset_index()
    fail_counts.columns = ["Subjects Failed", "Student Count"]
    return fail_counts

# Average Marks Calculation
import pandas as pd

def avg_marks(df):
    df[["SESMARK", "ESEM", "TOTMARK"]] = df[["SESMARK", "ESEM", "TOTMARK"]].apply(pd.to_numeric, errors="coerce")

    # ✅ Compute subcategory averages for SESMARK
    internal_avg = df.groupby("SUBTYPE")["SESMARK"].mean().reset_index()
    internal_avg["Mark Type"] = "SESMARK"  # Label as Internal
    internal_avg.rename(columns={"SESMARK": "Average Marks"}, inplace=True)

    # ✅ Map SUBTYPE to readable labels (Added "O" for Open Elective)
    subcategory_labels = {
        "T": "Theory (40)",
        "P": "Practical/Project (60)",
        "L": "Lab (60)",
        "S": "Single (100)",
        "O": "Other/Open Elective"
    }
    internal_avg["Subcategory"] = internal_avg["SUBTYPE"].map(subcategory_labels)

    # ✅ Compute ESEM & TOTMARK averages
    external_tot_avg = df[["ESEM", "TOTMARK"]].mean().reset_index()
    external_tot_avg.columns = ["Mark Type", "Average Marks"]
    external_tot_avg["Subcategory"] = external_tot_avg["Mark Type"].map({"ESEM": "External", "TOTMARK": "Total"})

    # ✅ Merge both datasets
    avg_data = pd.concat([internal_avg[["Mark Type", "Average Marks", "Subcategory"]], external_tot_avg], ignore_index=True)

    return avg_data


# Chart: Pass/Fail Count
# Chart: Pass/Fail Count
def pass_fail_chart(df):
    pass_fail_counts = df["Status"].value_counts().reset_index()
    pass_fail_counts.columns = ["Status", "Count"]

    # Enforce correct order manually
    pass_fail_counts = pass_fail_counts.set_index("Status").reindex(["Pass", "Fail"], fill_value=0).reset_index()

    total = pass_fail_counts["Count"].sum()
    pass_fail_counts["Percentage"] = pass_fail_counts["Count"] / total * 100  # Calculate percentage

    chart = alt.Chart(pass_fail_counts).mark_bar().encode(
        x=alt.X("Status:N", title="Pass/Fail", sort=["Pass", "Fail"]),  # Explicit sorting
        y=alt.Y("Count:Q", title="Number of Students"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=["Pass", "Fail"], range=["lightgreen", "lightcoral"])),
        tooltip=["Status", "Count", alt.Tooltip("Percentage:Q", title="Percentage", format=".1f")]
    ).properties(title=f"Pass/Fail Count (Total: {total})")

    text = chart.mark_text(dy=-10, fontSize=14, fontWeight="bold").encode(text="Count")

    return (chart + text)

# Chart: Fail Categories
def fail_categories_chart(df):
    # Define all possible categories
    fail_types = ["Prevention", "Malpractice", "Absent", "Attempted"]

    # Count fail types
    fail_categories = df["Fail Type"].value_counts().reindex(fail_types, fill_value=0).reset_index()
    fail_categories.columns = ["Category", "Count"]

    # Create the chart
    chart = alt.Chart(fail_categories).mark_bar().encode(
        x=alt.X("Category:N", title="Fail Category", sort=fail_types),
        y=alt.Y("Count:Q", title="Number of Students"),
        color=alt.Color("Category:N"),
        tooltip=["Category", "Count"]
    ).properties(title="Fail Categories Breakdown")

    text = chart.mark_text(dy=-10, fontSize=14, fontWeight="bold").encode(text="Count")

    return (chart + text)

import altair as alt

def avg_marks_chart(df):
    # ✅ Ensure correct order for Mark Type
    order = ["SESMARK", "ESEM", "TOTMARK"]
    df["Mark Type"] = pd.Categorical(df["Mark Type"], categories=order, ordered=True)

    # ✅ Handle SESMARK subcategories, but keep ESEM and TOTMARK as single bars
    df["Subcategory"] = df.apply(
        lambda row: row["Subcategory"] if row["Mark Type"] == "SESMARK" else row["Mark Type"], axis=1
    )

    # ✅ Define color mapping (including "O" for Open Elective)
    color_mapping = {
        "ESEM": "orange",
        "Theory (40)": "blue",
        "Practical/Project (60)": "lightblue",
        "Lab (60)": "cyan",
        "Single (100)": "darkblue",
        "Other/Open Elective": "purple",  # Added for "O"
        "TOTMARK": "green"
    }

    # ✅ Ensure correct order: External → Internal (All Subcategories) → Total
    category_order = ["ESEM", "Theory (40)", "Practical/Project (60)", "Lab (60)", "Single (100)", "Other/Open Elective", "TOTMARK"]

    # ✅ Remove null/missing subcategories to prevent blank x-axis labels
    df = df[df["Subcategory"].notna() & df["Subcategory"].isin(category_order)]

    # ✅ Base chart
    base_chart = alt.Chart(df.sort_values(["Mark Type", "Subcategory"])).encode(
        x=alt.X("Subcategory:N", title="", sort=category_order),  # ✅ Show category names under bars
        y=alt.Y("Average Marks:Q", title="Average Marks"),
        color=alt.Color("Subcategory:N", scale=alt.Scale(domain=category_order, range=[color_mapping[c] for c in category_order])),
        tooltip=["Subcategory", "Average Marks"]
    )

    # ✅ Bar chart
    bars = base_chart.mark_bar()

    # ✅ Text labels (values on top of bars)
    text = base_chart.mark_text(dy=-10, fontSize=12, fontWeight="bold").encode(text=alt.Text("Average Marks:Q", format=".1f"))

    # ✅ Final Chart (category names below bars, no null category)
    final_chart = alt.layer(bars, text).properties(title="Average Marks by Category")

    return final_chart







# Chart: Subjects Failed Per Student
def subjects_failed_chart(df):
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X("Subjects Failed:N", title="Subjects Failed"),
        y=alt.Y("Student Count:Q", title="Number of Students"),
        color=alt.Color("Subjects Failed:N", scale=alt.Scale(scheme="category20")),
        tooltip=["Subjects Failed", "Student Count"]
    ).properties(title="Number of Subjects Failed Per Student")

    text = chart.mark_text(dy=-10, fontSize=14, fontWeight="bold").encode(text="Student Count")

    return (chart + text)

# Chart: Grade Distribution
def grade_distribution_chart(df):
    grade_order = ["O", "A+", "A", "B+", "B", "C", "U"]
    df["GRADE"] = pd.Categorical(df["GRADE"], categories=grade_order, ordered=True)

    chart = alt.Chart(df.sort_values("GRADE")).mark_bar().encode(
        x=alt.X("GRADE:N", title="Grade", sort=grade_order),  # Explicit sorting
        y=alt.Y("Count:Q", title="Number of Students"),
        color=alt.Color("GRADE:N", scale=alt.Scale(domain=grade_order, scheme="category20")),
        tooltip=["GRADE", "Count"]
    ).properties(title="Grade Distribution")

    text = chart.mark_text(dy=-10, fontSize=14, fontWeight="bold").encode(text="Count")

    return (chart + text)


DEPT_PREFIX = {
    "Aerospace": "AE", "Automobile": "AU", "Electronics Comm": "EC", "Artificial Intelligence": "AZ",
    "Information Tech": "IT", "Inst Eng": "EI", "Mech": "ME", "Production": "PR", 
    "Robotics": "RO", "Rubber and Plastics": "RP"
}

# Streamlit UI
st.title("Student Performance Analysis")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)

    # Dropdowns
    # Define additional subjects for each department
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

# Dropdowns
    columns_to_keep = ["DEPNAME", "BRNAME", "SEM", "REGNO", "SUBCODE", "SUBTYPE", "SESMARK", "ESEM", "TOTMARK", "GRADE"]
    df = df[columns_to_keep].copy()
    department_options = ["Overall", "Others (Open Elective)"] + sorted(df["DEPNAME"].unique())
    selected_department = st.selectbox("Select Department", department_options)

    if selected_department == "Others (Open Elective)":
        selected_branch = "All"  # Hide branch selection
        all_prefixes = tuple(DEPT_PREFIX.values())  # Get all department prefixes

        # Filter out department subjects
        df_others = df[~df["SUBCODE"].str.startswith(all_prefixes)].copy()
        
        # Get unique subjects from the filtered dataset
        subject_list = sorted(df_others["SUBCODE"].unique())

        # Add extra subjects from different departments
        for subjects in extra_subjects.values():
            subject_list.extend(subjects)

        subject_list = sorted(set(subject_list))  # Remove duplicates and sort

        # ✅ Re-add extra subjects to df_others if they exist in the original df
        df_extra = df[df["SUBCODE"].isin(subject_list)]
        df_others = pd.concat([df_others, df_extra]).drop_duplicates()

        df = df_others  # Update df with the new filtered dataset
 # Remove duplicates and sort
    else:
        selected_branch = st.selectbox("Select Branch", ["All"] + sorted(df[df["DEPNAME"] == selected_department]["BRNAME"].unique())) if selected_department != "Overall" else "All"

        if selected_department != "Overall":
            df = df[df["DEPNAME"] == selected_department]

        if selected_branch != "All":
            df = df[df["BRNAME"] == selected_branch]

        subject_list = sorted(df["SUBCODE"].unique())

    selected_semester = st.selectbox("Select Semester", ["All", "5", "7"])

    if selected_semester != "All":
        df = df[df["SEM"] == int(selected_semester)]

    selected_subject = st.selectbox("Select Subject", ["All"] + subject_list)

    if selected_subject != "All":
        df = df[df["SUBCODE"] == selected_subject]



    # Generate Data for Charts
    pass_fail_df = determine_pass_fail(df)
    fail_df = categorize_failures(df)
    avg_marks_df = avg_marks(df)
    subjects_failed_df = subjects_failed(df)
    grade_dist_df = grade_distribution(df)

    # Display Charts
    st.subheader("1. Pass/Fail Count")
    st.altair_chart(pass_fail_chart(pass_fail_df), use_container_width=True)

    st.subheader("2. Fail Categories")
    st.altair_chart(fail_categories_chart(fail_df), use_container_width=True)

    st.subheader("3. Average Marks")
    st.altair_chart(avg_marks_chart(avg_marks_df), use_container_width=True)

    # Only show "Subjects Failed" if a subject is NOT selected
    if selected_subject == "All":
        st.subheader("4. Subjects Failed Per Student")
        st.altair_chart(subjects_failed_chart(subjects_failed_df), use_container_width=True)

    st.subheader("5. Grade Distribution")
    st.altair_chart(grade_distribution_chart(grade_dist_df), use_container_width=True)





# Display Footer
st.markdown("""
    <div class="footer-container">
        Dharshan S | 2021506018 | dharshans465@gmail.com
    </div>
""", unsafe_allow_html=True)


