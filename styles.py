import streamlit as st


def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

        *, html, body, [class*="st-"] {
            font-family: 'Assistant', sans-serif !important;
            direction: rtl !important;
        }

        [data-testid="stIconMaterial"],
        [data-testid="stExpanderToggleIcon"],
        [data-testid="stExpanderToggleIcon"] span,
        [data-testid="stIconMaterial"] span,
        .material-symbols-rounded {
            font-family: 'Material Symbols Rounded' !important;
            direction: ltr !important;
            unicode-bidi: bidi-override !important;
        }

        .stApp {
            background-color: #ffffff;
        }

        .main .block-container {
            max-width: 900px;
            padding: 0rem 1rem 2rem 1rem;
        }

        header[data-testid="stHeader"] {
            height: 0px !important;
            min-height: 0px !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        .stMainBlockContainer {
            padding-top: 0.5rem !important;
        }

        h1, h2, h3, h4, h5, h6 {
            text-align: right !important;
            color: #2c3e50 !important;
            font-family: 'Assistant', sans-serif !important;
        }

        p, span, label, div {
            text-align: right !important;
            font-family: 'Assistant', sans-serif !important;
        }

        .stMarkdown {
            direction: rtl !important;
        }

        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            direction: rtl !important;
            text-align: right !important;
            font-family: 'Assistant', sans-serif !important;
            border: 1px solid #d1d9e6 !important;
            border-radius: 10px !important;
            padding: 12px !important;
            font-size: 16px !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #7fb3d8 !important;
            box-shadow: 0 0 0 2px rgba(127, 179, 216, 0.2) !important;
        }

        .stButton > button {
            font-family: 'Assistant', sans-serif !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            border-radius: 12px !important;
            padding: 12px 28px !important;
            min-height: 48px !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px) !important;
        }

        /* Small delete buttons */
        button[kind="secondary"][data-testid="stBaseButton-secondary"]:has(+ div[data-testid]) {
            min-height: 32px !important;
            padding: 4px 8px !important;
            font-size: 14px !important;
        }

        /* Target delete buttons by their emoji content - narrow column buttons */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child .stButton > button {
            min-height: 32px !important;
            padding: 4px 10px !important;
            font-size: 13px !important;
            border-radius: 8px !important;
            background-color: transparent !important;
            border: 1px solid #e2e8f0 !important;
            color: #999 !important;
        }

        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child .stButton > button:hover {
            background-color: #fee2e2 !important;
            border-color: #fca5a5 !important;
            color: #ef4444 !important;
        }

        div[data-testid="stFileUploader"] {
            direction: rtl !important;
        }

        div[data-testid="stFileUploader"] section {
            direction: rtl !important;
        }

        .path-card {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px 20px;
            text-align: center !important;
            transition: all 0.3s ease;
            cursor: pointer;
            height: 180px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .path-card:hover {
            border-color: #7fb3d8;
            box-shadow: 0 4px 16px rgba(127, 179, 216, 0.15);
        }

        .path-card-icon {
            font-size: 36px;
            margin-bottom: 8px;
        }

        .path-card-title {
            font-size: 20px;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 4px;
        }

        .path-card-desc {
            font-size: 15px;
            color: #6b7c93;
            line-height: 1.6;
        }

        [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:first-of-type button[kind="secondary"] {
            background: #f8fafc !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 16px !important;
            padding: 30px 20px !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            color: #2c3e50 !important;
            height: 120px !important;
            transition: all 0.3s ease !important;
            white-space: normal !important;
            line-height: 1.4 !important;
        }

        [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:first-of-type button[kind="secondary"]:hover {
            border-color: #7fb3d8 !important;
            box-shadow: 0 4px 16px rgba(127, 179, 216, 0.15) !important;
            background: #f0f6fb !important;
        }

        .section-header {
            background: #f0f6fb;
            border-right: 4px solid #7fb3d8;
            padding: 8px 16px;
            border-radius: 0 10px 10px 0;
            margin: 8px 0 8px 0;
            font-size: 17px;
            font-weight: 700;
            color: #2c3e50;
        }

        .suggestion-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            margin: 12px 0;
        }

        .suggestion-label {
            font-size: 13px;
            font-weight: 600;
            color: #7fb3d8;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .original-text {
            background: #fff5f5;
            border-right: 3px solid #e88e8e;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin: 8px 0;
            color: #5a5a5a;
            font-size: 15px;
            line-height: 1.7;
        }

        .improved-text {
            background: #f0faf0;
            border-right: 3px solid #7fb3d8;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin: 8px 0;
            color: #2c3e50;
            font-size: 15px;
            line-height: 1.7;
        }

        .chat-message-user {
            background: #7fb3d8;
            color: white;
            padding: 14px 20px;
            border-radius: 16px 16px 4px 16px;
            margin: 8px 0;
            font-size: 15px;
            line-height: 1.6;
            max-width: 85%;
            margin-left: auto;
        }

        .chat-message-ai {
            background: #f0f6fb;
            color: #2c3e50;
            padding: 14px 20px;
            border-radius: 16px 16px 16px 4px;
            margin: 8px 0;
            font-size: 15px;
            line-height: 1.6;
            max-width: 85%;
            margin-right: auto;
        }

        .app-header {
            text-align: center !important;
            padding: 8px 0 4px 0;
        }

        .app-header h1 {
            text-align: center !important;
            font-size: 32px !important;
            font-weight: 800 !important;
            color: #2c3e50 !important;
            margin-bottom: 0px !important;
        }

        .app-header p {
            text-align: center !important;
            font-size: 15px;
            color: #6b7c93;
            margin-bottom: 0px !important;
        }

        .logo-text {
            color: #7fb3d8;
        }

        .step-indicator {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin: 8px 0;
            direction: ltr !important;
        }

        .step-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #e2e8f0;
        }

        .step-dot.active {
            background: #7fb3d8;
            width: 28px;
            border-radius: 5px;
        }

        .cv-preview {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .cv-preview h2 {
            text-align: center !important;
            color: #2c3e50 !important;
            font-size: 24px !important;
            margin-bottom: 4px !important;
        }

        .cv-preview h3 {
            color: #7fb3d8 !important;
            font-size: 18px !important;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 6px;
        }

        .back-btn {
            margin-bottom: 20px;
        }

        .stDownloadButton > button {
            background-color: #7fb3d8 !important;
            color: white !important;
            border: none !important;
            font-family: 'Assistant', sans-serif !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            border-radius: 12px !important;
            padding: 12px 28px !important;
            min-height: 48px !important;
            width: 100% !important;
        }

        .stDownloadButton > button:hover {
            background-color: #6a9fc4 !important;
        }

        div[data-testid="stExpander"] {
            direction: rtl !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            margin-bottom: 8px !important;
        }

        div[data-testid="stExpander"] summary {
            direction: rtl !important;
        }

        .stSpinner > div {
            direction: ltr !important;
        }

        @media (max-width: 768px) {
            .main .block-container {
                padding: 0.25rem 0.5rem 2rem 0.5rem;
            }

            .path-card {
                padding: 16px 12px;
                height: 160px;
            }

            .path-card-icon {
                font-size: 28px;
            }

            .path-card-title {
                font-size: 17px;
            }

            .app-header h1 {
                font-size: 26px !important;
            }

            .stButton > button {
                width: 100% !important;
                min-height: 52px !important;
                font-size: 17px !important;
            }

            .chat-message-user,
            .chat-message-ai {
                max-width: 95%;
            }
        }

        header[data-testid="stHeader"][class] {
            background: #ffffff !important;
            border-bottom: none !important;
        }

        div[data-testid="stSidebarContent"] {
            direction: rtl !important;
            background: #f8fafc !important;
        }
    </style>
    """, unsafe_allow_html=True)
