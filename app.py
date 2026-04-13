import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="Café Rewards Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    /* Page background */
    .stApp { background-color: #F8F4EF; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1B2A4A;
    }
    [data-testid="stSidebar"] * { color: #E2EAF4 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label { color: #9CA3AF !important; font-size: 12px !important; }

    /* KPI cards */
    .kpi-card {
        background: #1B2A4A;
        border: 2px solid #F4A26155;
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }
    .kpi-value { font-size: 28px; font-weight: 700; color: #F4A261; margin: 0; }
    .kpi-label { font-size: 12px; color: #9CA3AF; margin: 4px 0 0; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Header */
    .dash-header {
        background: #1B2A4A;
        border-radius: 10px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    .dash-title { font-size: 22px; font-weight: 700; color: #F4A261; margin: 0; }
    .dash-sub   { font-size: 12px; color: #9CA3AF; margin: 4px 0 0; }

    /* Section headers */
    .section-header {
        font-size: 13px;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 20px 0 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid #E5E7EB;
    }

    /* Remove streamlit default padding */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    div[data-testid="metric-container"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ─── COLORS ─────────────────────────────────────────────────────
COLORS = {
    "navy":   "#1B2A4A",
    "amber":  "#F4A261",
    "blue":   "#2E86AB",
    "teal":   "#2EC4B6",
    "coral":  "#E76F51",
    "sage":   "#52796F",
    "purple": "#7C5CBF",
    "gold":   "#E9C46A",
    "gray":   "#D1D5DB",
}
CHART_COLORS = [COLORS["blue"], COLORS["teal"], COLORS["coral"],
                COLORS["purple"], COLORS["amber"], COLORS["sage"]]

CHART_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Segoe UI, sans-serif", color="#374151"),
    title_font=dict(size=13, color="#1B2A4A"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(font=dict(size=11), orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)

# ─── LOAD DATA ──────────────────────────────────────────────────
@st.cache_data
def load_data():
    fact_txn  = pd.read_csv("data/fact_transactions.csv")
    fact_oe   = pd.read_csv("data/fact_offer_events.csv")
    dim_cust  = pd.read_csv("data/dim_customers.csv")
    dim_off   = pd.read_csv("data/dim_offers.csv")
    dim_date  = pd.read_csv("data/dim_date.csv")
    bridge    = pd.read_csv("data/bridge_customer_offer.csv")

    # Merge customer info into transactions
    fact_txn = fact_txn.merge(
        dim_cust[["customer_id","gender","age_group","income_group","membership_year"]],
        on="customer_id", how="left"
    )
    # Merge customer + offer info into offer events
    fact_oe = fact_oe.merge(
        dim_cust[["customer_id","gender","age_group","income_group"]],
        on="customer_id", how="left"
    )
    fact_oe = fact_oe.merge(
        dim_off[["offer_id","offer_type","difficulty","reward","roi_pct"]],
        on="offer_id", how="left"
    )
    return fact_txn, fact_oe, dim_cust, dim_off, dim_date, bridge

fact_txn, fact_oe, dim_cust, dim_off, dim_date, bridge = load_data()

# ─── SIDEBAR FILTERS ────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ☕ Café Rewards")
    st.markdown("---")

    st.markdown("### Filters")

    gender_opts = ["All"] + sorted(dim_cust["gender"].dropna().unique().tolist())
    gender = st.selectbox("Gender", gender_opts)

    age_order = ["<30","30-44","45-59","60-74","75+","Unknown"]
    age_opts  = [a for a in age_order if a in dim_cust["age_group"].unique()]
    age_sel   = st.multiselect("Age Group", age_opts, default=age_opts)

    inc_order  = ["<40K","40-60K","60-80K","80-120K","120K+","Unknown"]
    inc_opts   = [i for i in inc_order if i in dim_cust["income_group"].unique()]
    inc_sel    = st.multiselect("Income Group", inc_opts, default=inc_opts)

    offer_opts = ["All"] + sorted(dim_off["offer_type"].unique().tolist())
    offer_type = st.selectbox("Offer Type", offer_opts)

    week_opts = ["All"] + [f"Week {i}" for i in range(1,6)]
    week_sel  = st.selectbox("Week", week_opts)

    st.markdown("---")
    st.markdown("**Pages**")
    page = st.radio("", ["Overview","Customer","Offer","Revenue"], label_visibility="collapsed")

    st.markdown("---")
    st.caption("Data: Starbucks Rewards Dataset")
    st.caption("Built with Python · Streamlit · Plotly")

# ─── APPLY FILTERS ──────────────────────────────────────────────
def apply_filters(df, gender_col="gender", age_col="age_group", inc_col="income_group"):
    d = df.copy()
    if gender != "All" and gender_col in d.columns:
        d = d[d[gender_col] == gender]
    if age_sel and age_col in d.columns:
        d = d[d[age_col].isin(age_sel)]
    if inc_sel and inc_col in d.columns:
        d = d[d[inc_col].isin(inc_sel)]
    if week_sel != "All" and "week" in d.columns:
        wk = int(week_sel.split()[1])
        d = d[d["week"] == wk]
    return d

ftxn = apply_filters(fact_txn)
foe  = apply_filters(fact_oe)

def apply_offer_filter(df):
    d = df.copy()
    if offer_type != "All" and "offer_type" in d.columns:
        d = d[d["offer_type"] == offer_type]
    return d

foe_off = apply_offer_filter(foe)

# ─── KPI HELPER ─────────────────────────────────────────────────
def kpi_card(value, label, color=COLORS["amber"]):
    return f"""
    <div class="kpi-card">
        <p class="kpi-value" style="color:{color}">{value}</p>
        <p class="kpi-label">{label}</p>
    </div>"""

def fmt_currency(n):
    if n >= 1_000_000: return f"${n/1_000_000:.2f}M"
    if n >= 1_000:     return f"${n/1_000:.1f}K"
    return f"${n:.2f}"

def section(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

# ─── HEADER ─────────────────────────────────────────────────────
page_subtitles = {
    "Overview": "30-day campaign summary · all key metrics at a glance",
    "Customer": "demographics, segmentation & membership growth",
    "Offer":    "funnel analysis · BOGO vs Discount · ROI breakdown",
    "Revenue":  "daily trends · age × income heatmap · gender split",
}
st.markdown(f"""
<div class="dash-header">
    <div>
        <p class="dash-title">☕ Café Rewards — {page}</p>
        <p class="dash-sub">{page_subtitles[page]}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ════════════════════════════════════════════════════════════════
if page == "Overview":
    total_rev   = ftxn["amount"].sum()
    total_txn   = len(ftxn)
    active_cust = ftxn["customer_id"].nunique()
    received    = len(foe[foe["event_type"]=="offer received"])
    completed   = len(foe[foe["event_type"]=="offer completed"])
    comp_rate   = (completed/received*100) if received > 0 else 0
    view_rate   = (len(foe[foe["event_type"]=="offer viewed"])/received*100) if received > 0 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(kpi_card(fmt_currency(total_rev), "Total Revenue"), unsafe_allow_html=True)
    c2.markdown(kpi_card(f"{total_txn:,}", "Transactions"), unsafe_allow_html=True)
    c3.markdown(kpi_card(f"{active_cust:,}", "Active Customers"), unsafe_allow_html=True)
    c4.markdown(kpi_card(f"{comp_rate:.1f}%", "Completion Rate", COLORS["teal"]), unsafe_allow_html=True)
    c5.markdown(kpi_card(f"{view_rate:.1f}%", "View Rate", COLORS["coral"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        section("Revenue & Transaction Trend — 30 Days")
        daily = ftxn.groupby("day").agg(
            Revenue=("amount","sum"),
            Transactions=("customer_id","count")
        ).reset_index()
        daily = daily.merge(dim_date[["day","day_label"]], on="day", how="left")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=daily["day_label"], y=daily["Transactions"],
            name="Transactions", marker_color=COLORS["blue"], opacity=0.7), secondary_y=False)
        fig.add_trace(go.Scatter(x=daily["day_label"], y=daily["Revenue"],
            name="Revenue", line=dict(color=COLORS["amber"], width=2.5),
            mode="lines"), secondary_y=True)
        fig.update_layout(**CHART_LAYOUT, height=280)
        fig.update_xaxes(tickfont=dict(size=9), tickangle=45)
        fig.update_yaxes(title_text="Transactions", secondary_y=False, tickfont=dict(size=9))
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=True, tickfont=dict(size=9),
                         tickprefix="$")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section("Revenue by Gender")
        rev_gender = ftxn.groupby("gender")["amount"].sum().reset_index()
        rev_gender.columns = ["Gender","Revenue"]
        rev_gender = rev_gender[rev_gender["Gender"] != "Unknown"]
        color_map = {"F": COLORS["coral"], "M": COLORS["blue"], "O": COLORS["sage"]}
        fig2 = px.pie(rev_gender, values="Revenue", names="Gender",
                      hole=0.5, color="Gender", color_discrete_map=color_map)
        fig2.update_traces(textposition="outside", textinfo="percent+label",
                           textfont_size=11)
        fig2.update_layout(**CHART_LAYOUT, height=280,
                           showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns([2, 3])

    with col3:
        section("Offer Funnel")
        funnel_data = pd.DataFrame({
            "Stage": ["Received","Viewed","Completed"],
            "Count": [
                len(foe[foe["event_type"]=="offer received"]),
                len(foe[foe["event_type"]=="offer viewed"]),
                len(foe[foe["event_type"]=="offer completed"]),
            ]
        })
        fig3 = go.Figure(go.Funnel(
            y=funnel_data["Stage"], x=funnel_data["Count"],
            marker=dict(color=[COLORS["blue"], COLORS["teal"], COLORS["amber"]]),
            textinfo="value+percent initial",
            textfont=dict(size=12)
        ))
        fig3.update_layout(**CHART_LAYOUT, height=250)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        section("Customers by Age Group & Gender")
        age_gender = ftxn.groupby(["age_group","gender"])["customer_id"].nunique().reset_index()
        age_gender.columns = ["Age Group","Gender","Customers"]
        age_gender = age_gender[age_gender["Age Group"] != "Unknown"]
        age_gender = age_gender[age_gender["Gender"] != "Unknown"]
        age_order_f = ["<30","30-44","45-59","60-74","75+"]
        age_gender["Age Group"] = pd.Categorical(age_gender["Age Group"], categories=age_order_f, ordered=True)
        age_gender = age_gender.sort_values("Age Group")
        color_map2 = {"F": COLORS["coral"], "M": COLORS["blue"], "O": COLORS["sage"]}
        fig4 = px.bar(age_gender, x="Customers", y="Age Group", color="Gender",
                      orientation="h", barmode="stack", color_discrete_map=color_map2)
        fig4.update_layout(**CHART_LAYOUT, height=250)
        fig4.update_xaxes(tickfont=dict(size=10))
        fig4.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig4, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER
# ════════════════════════════════════════════════════════════════
elif page == "Customer":
    fcust = dim_cust.copy()
    if gender != "All":    fcust = fcust[fcust["gender"] == gender]
    if age_sel:            fcust = fcust[fcust["age_group"].isin(age_sel)]
    if inc_sel:            fcust = fcust[fcust["income_group"].isin(inc_sel)]

    total_mem = len(fcust)
    female    = len(fcust[fcust["gender"]=="F"])
    male      = len(fcust[fcust["gender"]=="M"])
    avg_age   = fcust["age"].mean()

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(kpi_card(f"{total_mem:,}", "Total Members"), unsafe_allow_html=True)
    c2.markdown(kpi_card(f"{female:,}", "Female Members", COLORS["coral"]), unsafe_allow_html=True)
    c3.markdown(kpi_card(f"{male:,}", "Male Members", COLORS["blue"]), unsafe_allow_html=True)
    c4.markdown(kpi_card(f"{avg_age:.0f} yrs", "Avg Age", COLORS["teal"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        section("Customers by Income Group")
        inc_order_f = ["<40K","40-60K","60-80K","80-120K","120K+","Unknown"]
        inc_count = fcust.groupby("income_group").size().reset_index(name="Count")
        inc_count["income_group"] = pd.Categorical(inc_count["income_group"], categories=inc_order_f, ordered=True)
        inc_count = inc_count.sort_values("income_group")
        inc_colors = [COLORS["blue"],COLORS["teal"],COLORS["purple"],
                      COLORS["amber"],COLORS["coral"],COLORS["gray"]]
        fig5 = px.treemap(inc_count, path=["income_group"], values="Count",
                          color="income_group",
                          color_discrete_sequence=inc_colors)
        fig5.update_traces(textfont_size=13)
        fig5.update_layout(**CHART_LAYOUT, height=280)
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        section("Gender Distribution")
        gen_count = fcust[fcust["gender"]!="Unknown"].groupby("gender").size().reset_index(name="Count")
        color_map3 = {"F": COLORS["coral"], "M": COLORS["blue"], "O": COLORS["sage"]}
        fig6 = px.pie(gen_count, values="Count", names="gender",
                      hole=0.5, color="gender", color_discrete_map=color_map3)
        fig6.update_traces(textposition="outside", textinfo="percent+label", textfont_size=12)
        fig6.update_layout(**CHART_LAYOUT, height=280, showlegend=False)
        st.plotly_chart(fig6, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        section("Active Customers by Age Group & Gender")
        age_g2 = fcust[fcust["age_group"]!="Unknown"][fcust["gender"]!="Unknown"]
        age_g2 = age_g2.groupby(["age_group","gender"]).size().reset_index(name="Count")
        age_g2["age_group"] = pd.Categorical(age_g2["age_group"],
            categories=["<30","30-44","45-59","60-74","75+"], ordered=True)
        age_g2 = age_g2.sort_values("age_group")
        color_map4 = {"F": COLORS["coral"], "M": COLORS["blue"], "O": COLORS["sage"]}
        fig7 = px.bar(age_g2, x="Count", y="age_group", color="gender",
                      orientation="h", barmode="stack", color_discrete_map=color_map4)
        fig7.update_layout(**CHART_LAYOUT, height=260)
        fig7.update_xaxes(tickfont=dict(size=10))
        fig7.update_yaxes(tickfont=dict(size=10), title=None)
        st.plotly_chart(fig7, use_container_width=True)

    with col4:
        section("Membership Growth by Year")
        mem_year = fcust.groupby("membership_year").size().reset_index(name="New Members")
        fig8 = px.line(mem_year, x="membership_year", y="New Members",
                       markers=True, color_discrete_sequence=[COLORS["teal"]])
        fig8.update_traces(line_width=2.5, marker_size=7)
        fig8.update_layout(**CHART_LAYOUT, height=260)
        fig8.update_xaxes(tickfont=dict(size=10), dtick=1)
        fig8.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig8, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 3 — OFFER
# ════════════════════════════════════════════════════════════════
elif page == "Offer":
    received_n  = len(foe_off[foe_off["event_type"]=="offer received"])
    viewed_n    = len(foe_off[foe_off["event_type"]=="offer viewed"])
    completed_n = len(foe_off[foe_off["event_type"]=="offer completed"])
    comp_rate2  = (completed_n/received_n*100) if received_n > 0 else 0
    view_rate2  = (viewed_n/received_n*100) if received_n > 0 else 0

    c1,c2,c3 = st.columns(3)
    c1.markdown(kpi_card(f"{received_n:,}", "Offers Received"), unsafe_allow_html=True)
    c2.markdown(kpi_card(f"{comp_rate2:.1f}%", "Completion Rate", COLORS["teal"]), unsafe_allow_html=True)
    c3.markdown(kpi_card(f"{view_rate2:.1f}%", "View Rate", COLORS["coral"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])

    with col1:
        section("Completion Rate Gauge")
        fig9 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(comp_rate2, 1),
            domain={"x":[0,1],"y":[0,1]},
            title={"text":"Completion %", "font":{"size":13,"color":"#1B2A4A"}},
            number={"suffix":"%","font":{"size":32,"color":"#1B2A4A"}},
            gauge={
                "axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#D1D5DB"},
                "bar":{"color":COLORS["teal"],"thickness":0.3},
                "bgcolor":"white",
                "borderwidth":1,
                "bordercolor":"#E5E7EB",
                "steps":[
                    {"range":[0,50],"color":"#F3F4F6"},
                    {"range":[50,100],"color":"#EFF6FF"},
                ],
                "threshold":{
                    "line":{"color":COLORS["coral"],"width":3},
                    "thickness":0.8,
                    "value":50
                }
            }
        ))
        fig9.update_layout(**CHART_LAYOUT, height=260)
        st.plotly_chart(fig9, use_container_width=True)

    with col2:
        section("Offers Received vs Completed by Type")
        recv_by = foe_off[foe_off["event_type"]=="offer received"].groupby("offer_type").size().reset_index(name="Received")
        comp_by = foe_off[foe_off["event_type"]=="offer completed"].groupby("offer_type").size().reset_index(name="Completed")
        merged  = recv_by.merge(comp_by, on="offer_type", how="left").fillna(0)
        fig10 = go.Figure()
        fig10.add_trace(go.Bar(name="Received",  x=merged["offer_type"], y=merged["Received"],
                               marker_color=COLORS["blue"]))
        fig10.add_trace(go.Bar(name="Completed", x=merged["offer_type"], y=merged["Completed"],
                               marker_color=COLORS["teal"]))
        fig10.update_layout(**CHART_LAYOUT, height=260, barmode="group")
        fig10.update_xaxes(tickfont=dict(size=11))
        fig10.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig10, use_container_width=True)

    section("Offer Catalogue — Difficulty, Reward & ROI")
    off_table = dim_off[["offer_type","difficulty","reward","duration",
                          "has_email","has_mobile","has_social","has_web","roi_pct"]].copy()
    off_table.columns = ["Type","Min Spend ($)","Reward ($)","Duration (days)",
                         "Email","Mobile","Social","Web","ROI %"]
    off_table = off_table.sort_values("ROI %", ascending=False)
    if offer_type != "All":
        off_table = off_table[off_table["Type"] == offer_type]

    def color_roi(val):
        if val == 100:  return "background-color: #D1FAE5; color: #065F46"
        if val >= 40:   return "background-color: #FEF3C7; color: #92400E"
        if val > 0:     return "background-color: #FEE2E2; color: #991B1B"
        return "color: #6B7280"

    styled = off_table.style.applymap(color_roi, subset=["ROI %"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    section("Offer Completion Rate by Channel")
    channels = ["Email","Mobile","Social","Web"]
    ch_rates  = []
    for ch, col in zip(channels, ["has_email","has_mobile","has_social","has_web"]):
        sub = foe_off[foe_off["offer_type"] != "informational"]
        sub2 = sub.merge(dim_off[["offer_id",col]], on="offer_id", how="left")
        sub2 = sub2[sub2[col]==1]
        r = len(sub2[sub2["event_type"]=="offer received"])
        c = len(sub2[sub2["event_type"]=="offer completed"])
        ch_rates.append({"Channel":ch, "Rate": round(c/r*100,1) if r>0 else 0})
    ch_df = pd.DataFrame(ch_rates)
    fig11 = px.bar(ch_df, x="Channel", y="Rate", text="Rate",
                   color_discrete_sequence=[COLORS["purple"]])
    fig11.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig11.update_layout(**CHART_LAYOUT, height=220)
    fig11.update_yaxes(range=[0,70], ticksuffix="%")
    st.plotly_chart(fig11, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 4 — REVENUE
# ════════════════════════════════════════════════════════════════
elif page == "Revenue":
    total_rev2  = ftxn["amount"].sum()
    rev_female  = ftxn[ftxn["gender"]=="F"]["amount"].sum()
    rev_male    = ftxn[ftxn["gender"]=="M"]["amount"].sum()
    rev_cust    = total_rev2 / ftxn["customer_id"].nunique() if ftxn["customer_id"].nunique() > 0 else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(kpi_card(fmt_currency(total_rev2), "Total Revenue"), unsafe_allow_html=True)
    c2.markdown(kpi_card(fmt_currency(rev_female), "Female Revenue", COLORS["coral"]), unsafe_allow_html=True)
    c3.markdown(kpi_card(fmt_currency(rev_male),   "Male Revenue",   COLORS["blue"]),  unsafe_allow_html=True)
    c4.markdown(kpi_card(fmt_currency(rev_cust),   "Revenue / Customer", COLORS["teal"]), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section("Daily Revenue & Transaction Volume — 30 Days")
    daily2 = ftxn.groupby("day").agg(
        Revenue=("amount","sum"),
        Transactions=("customer_id","count")
    ).reset_index()
    daily2 = daily2.merge(dim_date[["day","day_label"]], on="day", how="left")

    fig12 = make_subplots(specs=[[{"secondary_y": True}]])
    fig12.add_trace(go.Bar(x=daily2["day_label"], y=daily2["Transactions"],
        name="Transactions", marker_color=COLORS["blue"], opacity=0.65), secondary_y=False)
    fig12.add_trace(go.Scatter(x=daily2["day_label"], y=daily2["Revenue"],
        name="Revenue ($)", line=dict(color=COLORS["amber"], width=3),
        mode="lines+markers", marker=dict(size=4)), secondary_y=True)
    fig12.update_layout(**CHART_LAYOUT, height=280)
    fig12.update_xaxes(tickfont=dict(size=9), tickangle=45)
    fig12.update_yaxes(title_text="Transactions", secondary_y=False, tickfont=dict(size=9))
    fig12.update_yaxes(title_text="Revenue ($)", secondary_y=True,
                       tickfont=dict(size=9), tickprefix="$")
    st.plotly_chart(fig12, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        section("Revenue by Age Group × Income Group (Heatmap)")
        heat = ftxn[
            (ftxn["age_group"]!="Unknown") & (ftxn["income_group"]!="Unknown")
        ].groupby(["age_group","income_group"])["amount"].sum().reset_index()
        heat_pivot = heat.pivot(index="age_group", columns="income_group", values="amount").fillna(0)
        inc_cols_h = [c for c in ["<40K","40-60K","60-80K","80-120K","120K+"] if c in heat_pivot.columns]
        age_rows_h = [r for r in ["<30","30-44","45-59","60-74","75+"] if r in heat_pivot.index]
        heat_pivot = heat_pivot.reindex(index=age_rows_h, columns=inc_cols_h)

        fig13 = go.Figure(go.Heatmap(
            z=heat_pivot.values,
            x=heat_pivot.columns.tolist(),
            y=heat_pivot.index.tolist(),
            colorscale=[[0,"#EFF6FF"],[0.5,"#2E86AB"],[1,"#1B2A4A"]],
            text=[[f"${v/1000:.0f}K" for v in row] for row in heat_pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=11),
            showscale=False,
        ))
        fig13.update_layout(**CHART_LAYOUT, height=260)
        fig13.update_xaxes(tickfont=dict(size=10))
        fig13.update_yaxes(tickfont=dict(size=10))
        st.plotly_chart(fig13, use_container_width=True)

    with col2:
        section("Total Revenue by Membership Year")
        rev_year = ftxn.groupby("membership_year")["amount"].sum().reset_index()
        rev_year.columns = ["Year","Revenue"]
        rev_year = rev_year.dropna()
        rev_year["Year"] = rev_year["Year"].astype(int)
        fig14 = px.bar(rev_year, x="Year", y="Revenue",
                       text=rev_year["Revenue"].apply(lambda x: f"${x/1000:.0f}K"),
                       color_discrete_sequence=[COLORS["blue"]])
        fig14.update_traces(textposition="outside", textfont_size=10)
        fig14.update_layout(**CHART_LAYOUT, height=260)
        fig14.update_xaxes(dtick=1, tickfont=dict(size=10))
        fig14.update_yaxes(tickfont=dict(size=10), tickprefix="$")
        st.plotly_chart(fig14, use_container_width=True)

    section("Revenue Breakdown by Gender")
    rev_gen = ftxn[ftxn["gender"]!="Unknown"].groupby("gender")["amount"].sum().reset_index()
    rev_gen.columns = ["Gender","Revenue"]
    rev_gen["Pct"] = (rev_gen["Revenue"]/rev_gen["Revenue"].sum()*100).round(1)
    color_map5 = {"F":COLORS["coral"],"M":COLORS["blue"],"O":COLORS["sage"]}
    fig15 = px.bar(rev_gen, x="Gender", y="Revenue",
                   text=rev_gen["Revenue"].apply(fmt_currency),
                   color="Gender", color_discrete_map=color_map5)
    fig15.update_traces(textposition="outside", textfont_size=12)
    fig15.update_layout(**CHART_LAYOUT, height=220, showlegend=False)
    fig15.update_yaxes(tickprefix="$", tickfont=dict(size=10))
    st.plotly_chart(fig15, use_container_width=True)
