import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle #type: ignore
from reportlab.lib import colors #type: ignore
from reportlab.lib.styles import getSampleStyleSheet #type: ignore
from reportlab.lib import pagesizes #type: ignore
from reportlab.lib.units import inch #type: ignore
from io import BytesIO
import os
import base64

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

st.set_page_config(layout="wide")

LOGO_PATH = "42slogo.png"

# -------------------------------------------------
# CENTERED SIDE-BY-SIDE HEADER
# -------------------------------------------------

def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

if os.path.exists(LOGO_PATH):
    img_base64 = get_base64_image(LOGO_PATH)
    
    st.markdown(
    f"""
    <div style="
        display: flex; 
        align-items: center; 
        justify-content: center; 
        width: 100%; 
        gap: 17px;
    ">
        <img src="data:image/png;base64,{img_base64}" 
             style="height: 3.5em; width: auto; object-fit: contain;">
        <h1 style="margin: 0; font-size: 2.5em; line-height: 1;">
            Requirement Handling Form
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# SIDEBAR NAVIGATION
# -------------------------------------------------

with st.sidebar:
    st.markdown("### 🏢 Pages")
    st.markdown("---")
    
    # Multi-page navigation
    st.page_link("app.py", label="📋 Main Requirement Form", icon="📋")
    st.page_link("pages/1_Feasibility_Requirement.py", label="📊 Feasibility Assessment", icon="📊")
    st.page_link("pages/2_Decision_Mind_Map.py", label="🧠 Decision Mind Map", icon="🧠")
    
    st.markdown("---")
    st.markdown("### Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Clear Form", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    with col2:
        if st.button("💾 Save Draft", use_container_width=True):
            st.info("Draft saved locally", icon="✓")
    
    st.markdown("---")
    st.markdown("### Help & Info")
    with st.expander("📚 How to use this form?"):
        st.markdown("""
        1. **Fill Client Information** - Start with basic details
        2. **Select Modules** - Choose which modules you need
        3. **Configure Each Module** - Set up specific requirements
        4. **Review Summary** - Check the live summary section
        5. **Download PDF** - Export your requirement as PDF
        """)
    
    st.markdown("---")
    st.caption("Version 1.0 | Last Updated: Feb 2026")

# -------------------------------------------------
# UTILITIES
# -------------------------------------------------

def frequency_selector(label, key_prefix):
    st.markdown(f"**{label} Frequency Configuration**")

    freq = st.selectbox(
        f"{label} - Frequency",
        ["Daily", "Hourly"],
        key=f"{key_prefix}_freq"
    )

    hourly_count = None
    if freq == "Hourly":
        hourly_count = st.number_input(
            f"{label} - How many times per day?",
            min_value=1,
            key=f"{key_prefix}_hourly"
        )

    return freq, hourly_count


def calculate_risk(freq_string, volume_string):
    if not freq_string or not volume_string:
        return None

    # Frequency severity
    freq_score = 1
    if "Hourly" in freq_string:
        try:
            times = int(freq_string.split("(")[1].split()[0])
            freq_score = 3 if times > 6 else 2
        except:
            freq_score = 2

    # Volume severity
    vol_score = 1
    try:
        volume = int(str(volume_string).replace(",", ""))
        if volume <= 10000:
            vol_score = 1
        elif volume <= 50000:
            vol_score = 2
        else:
            vol_score = 3
    except:
        vol_score = 1

    total = freq_score + vol_score

    if total <= 2:
        return "LOW"
    elif total <= 4:
        return "MODERATE"
    else:
        return "CRITICAL"


def render_summary(data):
    st.markdown("---")
    st.markdown("## Live Requirement Summary")
 

    for section, content in data.items():
        with st.expander(section, expanded=True):
            for k, v in content.items():
                if v not in ["", None, [], {}]:
                    st.markdown(f"**{k}**: {v}")

    # Risk detection for Products + Trends
    if "Products + Trends" in data:
        pt = data["Products + Trends"]
        risk = calculate_risk(
            pt.get("Overall Frequency"),
            pt.get("Expected Volume")
        )

        if risk:
            st.markdown("---")
            st.markdown("## Crawl Load Risk Assessment")

            if risk == "LOW":
                st.success("LOW RISK – Infrastructure load is safe.")
            elif risk == "MODERATE":
                st.warning("MODERATE RISK – Monitor scaling & proxy usage.")
            else:
                st.error("CRITICAL RISK – High probability of infra saturation.")


def validate_required(client_name):
    if not client_name:
        st.error("Client Name is required.")
        st.stop()


PREDEFINED_DOMAINS = ["swiggy.com", "blinkit.com", "zepto.com", "amazon.in", "flipkart.in"]

def domain_selector(label, key_prefix):
    """Multi-select for domains with custom option"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected = st.multiselect(
            label,
            PREDEFINED_DOMAINS,
            key=f"{key_prefix}_domains"
        )
    
    with col2:
        custom = st.text_input(
            "+ Custom",
            placeholder="Add custom domain",
            key=f"{key_prefix}_custom_domain"
        )
    
    all_domains = selected.copy()
    if custom.strip():
        all_domains.append(custom.strip())
    
    return ", ".join(all_domains) if all_domains else ""


def generate_pdf(data):
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Image #type: ignore
    from reportlab.lib.styles import ParagraphStyle #type: ignore
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib.colors import HexColor #type: ignore
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=pagesizes.A4, topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles for colorful PDF
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a237e'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=HexColor('#ffffff'),
        backColor=HexColor('#1a237e'),
        spaceAfter=8,
        spaceBefore=8,
        leftIndent=6,
        fontName='Helvetica-Bold'
    )
    
    wrapped_style = ParagraphStyle(
        'Wrapped',
        parent=styles['Normal'],
        wordWrap='CJK',
        fontSize=9,
        alignment=TA_JUSTIFY
    )

    # Add logo if it exists
    try:
        if os.path.exists(LOGO_PATH):
            logo = Image(LOGO_PATH, width=1*inch, height=0.8*inch)
            elements.append(logo)
            elements.append(Spacer(1, 0.1 * inch))
    except:
        pass
    
    # Add title
    elements.append(Paragraph("<b>Requirement Handling Form</b>", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    color_index = 0
    colors_list = [HexColor('#f5f5f5'), HexColor('#eeeeee')]

    for section, content in data.items():
        # Section header with background color
        elements.append(Paragraph(f"{section}", section_style))
        elements.append(Spacer(1, 0.08 * inch))

        table_data = []
        from reportlab.platypus import Paragraph

        for k, v in content.items():
            value_str = str(v) if v else "-"
            table_data.append([
                Paragraph(k, wrapped_style), 
                Paragraph(value_str, wrapped_style)
            ])

        if table_data:
            table = Table(table_data, colWidths=[1.7 * inch, 4.3 * inch])
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("BACKGROUND", (0, 0), (-1, -1), colors_list[color_index % 2]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 0.15 * inch))
            color_index += 1

    doc.build(elements)
    buffer.seek(0)
    return buffer


# -------------------------------------------------
# LAYOUT
# -------------------------------------------------

left, right = st.columns([2, 1])
form_data = {}

# -------------------------------------------------
# LEFT PANEL (FORM)
# -------------------------------------------------

with left:

    st.markdown("---")

    # 1. CLIENT INFORMATION
    st.header("1. Client Information")

    client_name = st.text_input("Client Name *", placeholder="Enter client name")
    
    priority = st.radio(
        "Priority Level",
        ["High", "Medium", "Low"],
        horizontal=True
    )
    
    completion_date = st.date_input("Expected Project Completion Date")
    expected_market = st.text_input(
        "Target Market / Geography",
        placeholder="e.g., India, US, Southeast Asia"
    )

    form_data["Client Information"] = {
        "Client Name": client_name,
        "Priority Level": priority,
        "Expected Completion Date": str(completion_date),
        "Target Market": expected_market
    }

    validate_required(client_name)

    st.markdown("---")

    # 2. MODULES TO CRAWL
    st.header("2. Modules to Crawl")
    st.markdown("Select required modules:")

    modules = st.multiselect(
        "Modules",
        [
            "Products + Trends",
            "SOS (Search on Site)",
            "Reviews",
            "Price Violation",
            "Store ID Crawls",
            "Festive Sale Crawls"
        ],
        label_visibility="collapsed"
    )

    form_data["Modules Selected"] = {
        "Selected Modules": ", ".join(modules) if modules else "None"
    }

    st.markdown("---")

    # 3. PRODUCTS + TRENDS MODULE
    if "Products + Trends" in modules:
        st.header("3. PRODUCTS + TRENDS MODULE")

        pt = {}

        # Step 1: Crawl Type
        st.subheader("Step 1: Crawl Type")
        crawl_type = st.radio(
            "Select crawl type",
            ["Category-based (Category_ES)", "Input-based (URL/Input driven)"],
            label_visibility="collapsed"
        )
        pt["Crawl Type"] = crawl_type

        # Step 2: Domains
        st.markdown("---")
        st.subheader("Step 2: Domains")
        pt["Domains"] = domain_selector("Select Domains", "pt")

        freq, hourly = frequency_selector("Overall Crawl", "pt_overall")
        pt["Overall Frequency"] = (
            f"{freq} ({hourly} times/day)" if hourly else freq
        )

        if crawl_type == "Category-based (Category_ES)":
            st.markdown("---")
            st.subheader("A) Category_ES Based Crawl Configuration")

            # Index Frequency
            st.markdown("**Index Frequency**")
            col1, col2 = st.columns(2)
            
            with col1:
                prod_freq, prod_hourly = frequency_selector("Products Index", "pt_prod")
                pt["Products Index Frequency"] = (
                    f"{prod_freq} ({prod_hourly} times/day)" if prod_hourly else prod_freq
                )
            
            with col2:
                trend_freq, trend_hourly = frequency_selector("Trends Index", "pt_trend")
                pt["Trends Index Frequency"] = (
                    f"{trend_freq} ({trend_hourly} times/day)" if trend_hourly else trend_freq
                )

            if prod_hourly or trend_hourly:
                pt["Hourly Crawl Timings"] = st.text_input(
                    "Specify crawl hours (avoid off-hours overload)",
                    placeholder="Example: 9 AM, 12 PM, 3 PM, 6 PM"
                )

            # Trends Configuration
            st.markdown("**Trends Configuration**")
            pt["No of RSS Crawls"] = st.number_input(
                "Number of RSS crawls to push into Trends",
                min_value=0
            )
            pt["Expected Data Push Volume"] = st.text_input(
                "How much of products crawl needed to be pushed into trends?",
            )

            # Category Details
            st.markdown("**Category Details**")
            pt["Sample Category List"] = st.text_area(
                "Sample Category List (comma-separated)",
                placeholder="e.g., Electronics, Fashion, Home & Kitchen"
            )
            
            category_status = st.radio(
                "Is final client category list available?",
                ["Yes", "No"],
                key="pt_category_status"
            )
            if category_status == "Yes":
                pt["Client Category Sheet Link"] = st.text_input(
                    "Attach Sheet Link"
                )
            else:
                pt["Client Category Expected Date"] = st.date_input(
                    "Expected Date for category list"
                )

        else:  # Input Based
            st.markdown("---")
            st.subheader("B) Input-Based Crawl Configuration")

            # Products Crawl
            st.markdown("**Products Crawl**")
            need_product = st.radio(
                "Is products crawl required?",
                ["Yes", "No"],
                key="pt_input_products_needed"
            )
            pt["Products Crawl Needed"] = need_product

            if need_product == "Yes":
                p_freq, p_hourly = frequency_selector("Products Crawl", "pt_input_prod")
                pt["Products Crawl Frequency"] = (
                    f"{p_freq} ({p_hourly} times/day)" if p_hourly else p_freq
                )

            # Trends Crawl
            st.markdown("**Trends Crawl Frequency**")
            t_freq, t_hourly = frequency_selector("Trends Crawl", "pt_input_trend")
            pt["Trends Crawl Frequency"] = (
                f"{t_freq} ({t_hourly} times/day)" if t_hourly else t_freq
            )

            if t_hourly:
                pt["Trends Hourly Timings"] = st.text_input(
                    "Specify crawl times if hourly",
                    placeholder="Example: 10 AM, 2 PM, 6 PM, 10 PM"
                )

            # Inputs
            st.markdown("**Inputs**")
            pt["Sample Input URLs"] = st.text_area(
                "Sample Input URLs",
                placeholder="If client inputs not available, provide testing URLs"
            )
            
            inputs_status = st.radio(
                "Client Inputs Status",
                ["Not Yet Provided", "Available - See Link Below"],
                key="pt_inputs_status"
            )
            if inputs_status == "Not Yet Provided":
                pt["Client Inputs Expected Date"] = st.date_input(
                    "Expected delivery date for inputs"
                )
            else:
                pt["Client Inputs Sheet Link"] = st.text_input(
                    "Attach Sheet Link with client inputs"
                )

            # Location Dependency
            st.markdown("**Location Dependency**")
            is_pincode_based = st.radio(
                "Is crawl Pincode/Zipcode based?",
                ["Yes", "No"],
                key="pt_pincode_based"
            )
            pt["Pincode Based"] = is_pincode_based
            if is_pincode_based == "Yes":
                pt["Sample Pincode"] = st.text_input(
                    "Sample Pincode",
                    placeholder="e.g., 110001, 560001"
                )
                pt["Client Pincode List Link"] = st.text_input(
                    "Client provided pincode list link (if available)"
                )

            # Volume & Output
            st.markdown("**Volume & Output**")
            pt["Expected Volume"] = st.text_input(
                "Expected Volume (Products / Pages per day)",
                placeholder="e.g., 1000 products/day"
            )
            
            pt["Screenshot Required"] = st.radio(
                "Is Screenshot Required?",
                ["Yes", "No"],
                key="pt_screenshot"
            )

        # Other Specific Fields
        st.markdown("**Any Specific Fields to Capture?**")
        pt["Specific Fields"] = st.text_area(
            "Specify any additional fields",
            placeholder="Example: seller name, discount %, stock status, rating breakdown, delivery time, search results ranking",
            key="pt_specific_fields"
        )

        form_data["Products + Trends"] = pt

        st.markdown("---")

    # 4. SOS MODULE
    if "SOS (Search on Site)" in modules:
        st.header("4. SOS (Search On Site) MODULE")

        sos = {}

        # Keywords
        st.markdown("**Keywords**")
        sos["No. of Keywords"] = st.number_input(
            "Number of Keywords",
            min_value=0,
            key="sos_keyword_count"
        )
        
        keywords_source = st.radio(
            "SOS Keywords List",
            ["Client Provided", "Provide Sample for Testing"],
            key="sos_keywords_source"
        )
        
        if keywords_source == "Client Provided":
            sos["SOS Keywords Sheet Link"] = st.text_input(
                "Attach Link to client keywords"
            )
        else:
            sos["Sample Keywords"] = st.text_area(
                "Provide sample keywords for testing",
                placeholder="e.g., laptop, shoes, home appliances"
            )

        # Domains
        st.markdown("**Domains**")
        sos["Domains"] = domain_selector("Select Domains", "sos")

        # Zipcode
        st.markdown("**Zipcode Required?**")
        sos["Zipcode Required"] = st.radio(
            "Is Zipcode required?",
            ["Yes", "No"],
            horizontal=True,
            key="sos_zipcode_required"
        )
        if sos["Zipcode Required"] == "Yes":
            sos["Pincode List"] = st.text_area(
                "Pincode List (comma-separated or sheet link)",
                placeholder="e.g., 110001, 560001, 400001"
            )

        # Crawl Depth
        st.markdown("**Crawl Depth**")
        col1, col2 = st.columns(2)
        with col1:
            sos["No. of Pages"] = st.number_input(
                "Number of Pages per keyword",
                min_value=1,
                value=1,
                key="sos_pages"
            )
        with col2:
            sos["No. of Products"] = st.number_input(
                "Number of Products per keyword",
                min_value=1,
                value=10,
                key="sos_products"
            )

        # Frequency
        st.markdown("**Frequency**")
        freq, hourly = frequency_selector("SOS Crawl", "sos")
        sos["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq

        form_data["SOS (Search on Site)"] = sos

        st.markdown("---")

    # 5. REVIEWS MODULE
    if "Reviews" in modules:
        st.header("5. REVIEWS MODULE")

        rev = {}
        
        rev["Domains"] = domain_selector("Select Domains", "reviews")

        st.markdown("**Review Source Type**")
        rev["Input Sources"] = st.multiselect(
            "Where to take review inputs from?",
            [
                "From Products Index",
                "From Trends Index",
                "From Review Input URLs",
                "Category-based Reviews Crawl"
            ],
            key="rev_source"
        )

        if "From Review Input URLs" in rev["Input Sources"]:
            rev["Sample Review URLs"] = st.text_area(
                "Sample Review URLs (for testing)",
                placeholder="Provide product review page URLs"
            )

        st.markdown("**Frequency**")
        freq, hourly = frequency_selector("Reviews Crawl", "rev")
        rev["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq
        
        if hourly:
            rev["Hourly Timings"] = st.text_input(
                "Specify timing if hourly",
                placeholder="Example: 8 AM, 12 PM, 6 PM, 10 PM"
            )

        form_data["Reviews"] = rev

        st.markdown("---")

    # 6. PRICE VIOLATION MODULE
    if "Price Violation" in modules:
        st.header("6. PRICE VIOLATION MODULE")

        pv = {}
        
        pv["Domains"] = domain_selector("Select Domains", "pv")

        st.markdown("**Frequency**")
        freq, hourly = frequency_selector("Price Violation Crawl", "pv")
        pv["Frequency"] = f"{freq} ({hourly} times/day)" if hourly else freq

        st.markdown("**Inputs**")
        pv["Product URL List"] = st.text_area(
            "Product URL List",
            placeholder="Provide sample product URLs to monitor"
        )
        
        pv["Zipcode Required"] = st.radio(
            "Zipcode required?",
            ["Yes", "No"],
            horizontal=True,
            key="pv_zipcode_required"
        )
        if pv["Zipcode Required"] == "Yes":
            pv["Zipcode List"] = st.text_area(
                "Zipcode List",
                placeholder="e.g., 110001, 560001, 400001"
            )
        
        pv["Price Violation Condition"] = st.text_area(
            "Price Violation Condition",
            placeholder="Example: MRP > X, Discount < Y%, Below competitor price, Price difference > 15%"
        )

        st.markdown("**Sample Inputs / Testing Data**")
        pv["Sample Inputs Sheet Link"] = st.text_input(
            "Sample Inputs Sheet Link (if available)",
            placeholder="Link to sample product data"
        )
        
        pv["Screenshot Required"] = st.radio(
            "Is Screenshot Required?",
            ["Yes", "No"],
            key="pv_screenshot"
        )

        form_data["Price Violation"] = pv

        st.markdown("---")

    # 7. STORE ID CRAWL
    if "Store ID Crawls" in modules:
        st.header("7. STORE ID CRAWL")

        storeid = {}
        
        storeid["Domains"] = domain_selector("Select Domains", "storeid")
        
        st.markdown("**Specific Store Locations**")
        storeid["Specific Location Required"] = st.radio(
            "Any specific store locations?",
            ["No", "Yes"],
            horizontal=True,
            key="storeid_location"
        )
        if storeid["Specific Location Required"] == "Yes":
            storeid["Location Details"] = st.text_area(
                "Specify location details",
                placeholder="e.g., Bangalore, Mumbai, Delhi"
            )

        st.markdown("**Store ID List**")
        storeid_status = st.radio(
            "Specific Pincode available?",
            ["Yes", "No"],
            key="storeid_list_status"
        )
        if storeid_status == "Yes":
            storeid["Specific Pincode List Link"] = st.text_input(
                "Attach Link"
            )

        form_data["Store ID Crawls"] = storeid

        st.markdown("---")

    # 8. FESTIVE SALE CRAWLS
    if "Festive Sale Crawls" in modules:
        st.header("8. FESTIVE SALE CRAWLS")

        festive = {}
        
        st.markdown("**Crawl Type**")
        festive["Crawl Type"] = st.radio(
            "Select crawl type",
            [
                "Products + Trends Based",
                "SOS Type",
                "Category URL Based"
            ],
            key="festive_type",
            label_visibility="collapsed"
        )

        if festive["Crawl Type"] == "Products + Trends Based":
            festive["Domains"] = domain_selector("Select Domains", "festive")
        elif festive["Crawl Type"] == "Category URL Based":
            festive["Category URL List"] = st.text_area(
                "Category URL List",
                placeholder="Provide category URLs for festive crawl"
            )

        st.markdown("**Schedule**")
        col1, col2, col3 = st.columns(3)
        with col1:
            festive["Frequency Per Day"] = st.number_input(
                "Frequency per Day",
                min_value=1,
                value=1,
                key="festive_freq"
            )
        with col2:
            festive["Start Date"] = st.date_input(
                "Start Date",
                key="festive_start"
            )
        with col3:
            festive["End Date"] = st.date_input(
                "End Date",
                key="festive_end"
            )

        form_data["Festive Sale Crawls"] = festive

        st.markdown("---")

    # 9. FINAL ALIGNMENT
    st.header("9. FINAL ALIGNMENT")

    form_data["Final Alignment"] = {
        "Client Core Objective": st.text_area(
            "What is the Client's Core Objective?",
            placeholder="Example: Market gap analysis, brand monitoring, competitive pricing intelligence, inventory visibility, demand trends, etc.",
            key="final_objective"
        ),
        "Expectations From Us": st.text_area(
            "What Are You Expecting From Us?",
            placeholder="Example: Real-time dashboards, daily reports, anomaly alerts, historical insights, competitive benchmarking, etc.",
            key="final_expectation"
        )
    }

    st.markdown("---")

    # 10. COMMENTS / NOTES
    st.header("10. Comments / Notes")

    form_data["Comments & Notes"] = {
        "Additional Comments": st.text_area(
            "Add any additional notes or comments",
            placeholder="Any other important details or special instructions...",
            key="final_comments"
        )
    }

    st.divider()

    if st.button("Generate and Download PDF"):
        pdf = generate_pdf(form_data)
        st.download_button(
            label="Download Requirement PDF",
            data=pdf,
            file_name=f"{client_name}_Requirement_Form.pdf",
            mime="application/pdf"
        )

# -------------------------------------------------
# RIGHT PANEL (LIVE SUMMARY)
# -------------------------------------------------

with right:
    render_summary(form_data)
