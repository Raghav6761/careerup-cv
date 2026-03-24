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
            color: #1a1a2e !important;
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
            border: 1.5px solid #e0e4ea !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-size: 16px !important;
            background: #ffffff !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #022559 !important;
            box-shadow: 0 0 0 3px rgba(2, 37, 89, 0.1) !important;
        }

        /* Primary buttons - filled blue */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            font-family: 'Assistant', sans-serif !important;
            font-weight: 700 !important;
            font-size: 18px !important;
            border-radius: 14px !important;
            padding: 14px 32px !important;
            min-height: 56px !important;
            background: #022559 !important;
            color: #ffffff !important;
            border: none !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 2px 8px rgba(2, 37, 89, 0.2) !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background: #011840 !important;
            box-shadow: 0 4px 16px rgba(2, 37, 89, 0.3) !important;
            transform: translateY(-1px) !important;
        }

        /* Secondary buttons - outlined */
        .stButton > button[kind="secondary"],
        .stButton > button[data-testid="stBaseButton-secondary"] {
            font-family: 'Assistant', sans-serif !important;
            font-weight: 700 !important;
            font-size: 18px !important;
            border-radius: 14px !important;
            padding: 14px 32px !important;
            min-height: 56px !important;
            background: #ffffff !important;
            color: #022559 !important;
            border: 2px solid #022559 !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        }

        .stButton > button[kind="secondary"]:hover,
        .stButton > button[data-testid="stBaseButton-secondary"]:hover {
            background: #eef1f6 !important;
            border-color: #011840 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12) !important;
        }

        /* Homepage CTA cards */
        .home-cta-card {
            padding: 22px 24px 14px 24px;
            border-radius: 14px 14px 0 0;
            text-align: center;
            direction: rtl;
            font-family: 'Assistant', sans-serif;
            margin-top: 24px;
            min-height: 110px;
        }

        .home-cta-card-primary {
            background: #022559;
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(2, 37, 89, 0.2);
        }

        .home-cta-card-secondary {
            background: #80d6c5;
            color: #022559;
            border: 2px solid #022559;
            border-bottom: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .home-cta-title {
            font-weight: 700;
            font-size: 18px;
            line-height: 1.3;
            display: block;
            margin-bottom: 6px;
        }

        .home-cta-desc {
            font-size: 13px;
            font-weight: 400;
            line-height: 1.4;
            display: block;
        }

        .home-cta-card-primary .home-cta-desc {
            color: rgba(255, 255, 255, 0.82);
        }

        .home-cta-card-secondary .home-cta-desc {
            color: #022559;
        }

        /* Style the native CTA buttons to match the cards below them */
        [data-testid="stColumn"]:first-child [data-testid="stBaseButton-primary"] {
            border-radius: 0 0 14px 14px !important;
            background: #011840 !important;
            border: none !important;
            margin-top: -4px !important;
        }

        [data-testid="stColumn"]:last-child [data-testid="stBaseButton-secondary"] {
            border-radius: 0 0 14px 14px !important;
            background: #6acbb8 !important;
            border: 2px solid #022559 !important;
            border-top: none !important;
            color: #022559 !important;
            margin-top: -4px !important;
        }

        /* Bare icon delete buttons using tertiary type */
        button[data-testid="stBaseButton-tertiary"] {
            min-height: 0px !important;
            height: auto !important;
            padding: 2px !important;
            font-size: 15px !important;
            line-height: 1 !important;
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: #ccc !important;
            cursor: pointer !important;
            opacity: 0.7 !important;
        }

        button[data-testid="stBaseButton-tertiary"]:hover {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            color: #ef4444 !important;
            opacity: 1 !important;
            transform: none !important;
        }

        div[data-testid="stFileUploader"] {
            direction: rtl !important;
        }

        div[data-testid="stFileUploader"] section {
            direction: rtl !important;
        }

        .section-header {
            background: #f0f6ff;
            border-right: 4px solid #022559;
            padding: 8px 16px;
            border-radius: 0 10px 10px 0;
            margin: 8px 0 8px 0;
            font-size: 17px;
            font-weight: 700;
            color: #1a1a2e;
        }

        .suggestion-card {
            background: #fafbfc;
            border: 1px solid #e0e4ea;
            border-radius: 14px;
            padding: 20px;
            margin: 12px 0;
        }

        .suggestion-label {
            font-size: 13px;
            font-weight: 600;
            color: #022559;
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
            line-height: 1.75;
            direction: rtl;
            text-align: right;
        }

        .original-text div, .original-text span {
            direction: rtl !important;
            text-align: right !important;
            font-family: 'Assistant', sans-serif !important;
            font-size: 15px;
            color: #5a5a5a;
        }

        .improved-text {
            background: #f0faf0;
            border-right: 3px solid #022559;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin: 8px 0;
            color: #1a1a2e;
            font-size: 15px;
            line-height: 1.75;
            direction: rtl;
            text-align: right;
        }

        .improved-text div, .improved-text span {
            direction: rtl !important;
            text-align: right !important;
            font-family: 'Assistant', sans-serif !important;
            font-size: 15px;
        }

        .chat-message-user {
            background: #022559;
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
            background: #f0f6ff;
            color: #1a1a2e;
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
            padding: 24px 0 20px 0;
        }

        .app-header h1 {
            text-align: center !important;
            font-size: 38px !important;
            font-weight: 800 !important;
            margin-bottom: 4px !important;
            letter-spacing: -0.5px !important;
        }

        .logo-cv {
            color: #1a1a2e !important;
        }

        .logo-ai {
            color: #80d6c5 !important;
        }

        .app-header p {
            text-align: center !important;
            font-size: 16px;
            color: #6b7280;
            margin-bottom: 0px !important;
            font-weight: 400;
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
            background: #e0e4ea;
        }

        .step-dot.active {
            background: #022559;
            width: 28px;
            border-radius: 5px;
        }

        .cv-preview {
            background: #ffffff;
            border: 1px solid #e0e4ea;
            border-radius: 14px;
            padding: 28px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }

        .cv-preview h2 {
            text-align: center !important;
            color: #1a1a2e !important;
            font-size: 24px !important;
            margin-bottom: 4px !important;
        }

        .cv-preview h3 {
            color: #022559 !important;
            font-size: 18px !important;
            border-bottom: 2px solid #e0e4ea;
            padding-bottom: 6px;
        }

        .btn-caption {
            text-align: center;
            font-size: 13px;
            color: #888888;
            margin-top: 6px;
            margin-bottom: 0;
            direction: rtl;
        }

        .back-btn {
            margin-bottom: 20px;
        }

        .stDownloadButton > button {
            background-color: #022559 !important;
            color: white !important;
            border: none !important;
            font-family: 'Assistant', sans-serif !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            border-radius: 14px !important;
            padding: 14px 28px !important;
            min-height: 52px !important;
            width: 100% !important;
            box-shadow: 0 2px 8px rgba(2, 37, 89, 0.2) !important;
            transition: all 0.25s ease !important;
        }

        .stDownloadButton > button:hover {
            background-color: #011840 !important;
            box-shadow: 0 4px 16px rgba(2, 37, 89, 0.3) !important;
        }

        div[data-testid="stExpander"] {
            direction: rtl !important;
            border: 1px solid #e0e4ea !important;
            border-radius: 14px !important;
            margin-bottom: 8px !important;
        }

        div[data-testid="stExpander"] summary {
            direction: rtl !important;
        }

        .stSpinner > div {
            direction: ltr !important;
        }

        .stTextArea div[data-testid="InputInstructions"] {
            display: none !important;
        }

        @media (max-width: 768px) {
            .main .block-container {
                padding: 0.25rem 0.5rem 2rem 0.5rem;
            }

            .app-header h1 {
                font-size: 30px !important;
            }

            .stButton > button {
                min-height: 52px !important;
                font-size: 17px !important;
            }

            button[data-testid="stBaseButton-tertiary"] {
                min-height: 0px !important;
                width: auto !important;
                font-size: 15px !important;
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
            background: #fafbfc !important;
        }
    </style>
    """, unsafe_allow_html=True)
