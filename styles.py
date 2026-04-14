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

        [class*="st-key-_cv_storage_"],
        [class*="st-key-auto_reload_improve"] {
            height: 0 !important;
            min-height: 0 !important;
            overflow: hidden !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            line-height: 0 !important;
        }
        [class*="st-key-_cv_storage_"] iframe,
        [class*="st-key-auto_reload_improve"] iframe {
            display: none !important;
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

        /* Radio buttons — ensure Assistant font on labels */
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] span,
        [data-testid="stRadio"] p {
            font-family: 'Assistant', sans-serif !important;
            font-size: 16px !important;
        }

        /* Selectbox / multiselect */
        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label,
        .stSelectbox div,
        [data-baseweb="select"] span {
            font-family: 'Assistant', sans-serif !important;
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
            position: relative;
        }

        .home-cta-card-primary {
            background: #2b56e0;
            color: #ffffff;
            box-shadow: 0 4px 16px rgba(43, 86, 224, 0.28);
        }

        .home-cta-card-secondary {
            background: #ffffff;
            color: #022559;
            border: 2px solid #2b56e0;
            border-bottom: none;
            box-shadow: 0 2px 8px rgba(43, 86, 224, 0.10);
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
            color: rgba(255, 255, 255, 0.85);
        }

        .home-cta-card-secondary .home-cta-desc {
            color: #3a4a6b;
        }

        /* Style the native CTA buttons — scoped to home_cta container only */
        [class*="st-key-home_cta"] [data-testid="column"]:first-child [data-testid="stBaseButton-primary"],
        [class*="st-key-home_cta"] [data-testid="stColumn"]:first-child [data-testid="stBaseButton-primary"] {
            border-radius: 0 0 14px 14px !important;
            background: #1a40c4 !important;
            border: none !important;
            margin-top: -4px !important;
        }

        [class*="st-key-home_cta"] [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"],
        [class*="st-key-home_cta"] [data-testid="stColumn"]:last-child [data-testid="stBaseButton-secondary"] {
            border-radius: 0 0 14px 14px !important;
            background: #f0f4ff !important;
            border: 2px solid #2b56e0 !important;
            border-top: none !important;
            color: #022559 !important;
            margin-top: -4px !important;
        }

        [class*="st-key-home_cta"] [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]:hover,
        [class*="st-key-home_cta"] [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]:active,
        [class*="st-key-home_cta"] [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]:focus,
        [class*="st-key-home_cta"] [data-testid="stColumn"]:last-child [data-testid="stBaseButton-secondary"]:hover {
            background: #f0f4ff !important;
            border: 2px solid #022559 !important;
            border-top: none !important;
            color: #022559 !important;
        }

        /* Equal-height compare cards in improve_review */
        [class*="st-key-cmprow_"] [data-testid="stHorizontalBlock"] {
            align-items: stretch !important;
        }
        [class*="st-key-cmprow_"] [data-testid="column"] {
            display: flex !important;
            flex-direction: column !important;
        }
        [class*="st-key-cmprow_"] [data-testid="column"] > div {
            display: flex !important;
            flex-direction: column !important;
            flex: 1 !important;
        }
        [class*="st-key-cmprow_"] [data-testid="stMarkdownContainer"] {
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
        }
        [class*="st-key-cmprow_"] .cmp-card {
            flex: 1 !important;
        }

        .e1mwqyj92 {
            background-color: #80d6c5 !important;
        }

        .e12zf7d53 {
            border-color: #80d6c5 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-card_upload),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-card_language),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-card_target) {
            background-color: #f2f1ef !important;
            border-color: #f2f1ef !important;
            border-radius: 12px !important;
            border-width: 2px !important;
        }

        [class*="st-key-card_upload"],
        [class*="st-key-card_language"],
        [class*="st-key-card_target"] {
            background-color: #f2f1ef !important;
        }

        div:has(> [class*="st-key-card_upload"]),
        div:has(> [class*="st-key-card_language"]),
        div:has(> [class*="st-key-card_target"]) {
            background-color: #f2f1ef !important;
            border-color: #f2f1ef !important;
        }

        /* Delete confirmation buttons — compact, equal height */
        [class*="st-key-confirm_del"] button,
        [class*="st-key-cancel_del"] button {
            font-size: 14px !important;
            padding: 8px 14px !important;
            min-height: 38px !important;
            height: 38px !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
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
            background: #ffffff;
            padding: 8px 16px;
            border-radius: 10px;
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

        .progress-container {
            margin: 10px 0 20px 0;
            width: 100%;
        }

        .progress-label {
            font-size: 13px;
            color: #6b7c93;
            font-weight: 600;
            margin-bottom: 6px;
            text-align: center;
        }

        .progress-track {
            width: 100%;
            height: 5px;
            background: #e2e8f0;
            border-radius: 999px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: #022559;
            border-radius: 999px;
            transition: width 0.3s ease;
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

        [data-testid="InputInstructions"] {
            display: none !important;
        }

        /* ── Mobile tabs for review page ── */
        .cv-dt  { display: block; }
        .cv-mob { display: none;  }

        @media (max-width: 768px) {
            .cv-dt  { display: none  !important; }
            .cv-mob { display: block !important; }
        }

        /* hide radio inputs entirely */
        .cv-tr { display: none !important; }

        /* tab bar */
        .cv-tab-bar {
            display: flex;
            direction: rtl;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            border: 1.5px solid #e0e4ea;
            border-bottom: none;
        }
        .cv-tl {
            flex: 1;
            padding: 10px 6px;
            text-align: center;
            cursor: pointer;
            background: #f5f7fa;
            font-size: 13px;
            font-weight: 600;
            color: #022559;
            transition: background 0.15s, color 0.15s;
            border-left: 1px solid #e0e4ea;
        }
        .cv-tl:last-child { border-left: none; }

        /* tab content panels (hidden by default) */
        .cv-tc {
            display: none;
            padding: 14px;
            border: 1.5px solid #e0e4ea;
            border-radius: 0 0 10px 10px;
            font-size: 13px;
            line-height: 1.8;
            direction: rtl;
            text-align: right;
        }

        /* active tab label */
        input[id^="cv-t-impr-"]:checked ~ .cv-tab-bar label[for^="cv-t-impr-"],
        input[id^="cv-t-orig-"]:checked ~ .cv-tab-bar label[for^="cv-t-orig-"] {
            background: #022559;
            color: #ffffff;
        }

        /* show active content panel */
        input[id^="cv-t-impr-"]:checked ~ .cv-tc-impr { display: block; }
        input[id^="cv-t-orig-"]:checked ~ .cv-tc-orig { display: block; }

        /* legend row inside mobile tab */
        .cv-legend {
            font-size: 11px;
            color: #666;
            direction: rtl;
            text-align: right;
            margin-bottom: 8px;
            display: flex;
            gap: 14px;
            justify-content: flex-end;
            align-items: center;
        }

    </style>
    """, unsafe_allow_html=True)
