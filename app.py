import streamlit as st
import pandas as pd
import os
from typing import Any
from s3_utils import (
    create_s3_client,
    verify_bucket_existence,
    upload_file,
    list_files,
    download_file,
    delete_file,
    get_bucket_size,
    format_size,
    get_file_icon,
)

st.set_page_config(
    page_title="Cloud Vault S3 Console",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --bg: #07111f;
            --panel: rgba(10, 20, 40, 0.82);
            --panel-strong: rgba(18, 33, 61, 0.95);
            --accent: #5eead4;
            --accent-2: #60a5fa;
            --text: #f8fafc;
            --muted: #9fb0c8;
            --border: rgba(148, 163, 184, 0.22);
        }

        .block-container {
            padding-top: 3.8rem;
            padding-bottom: 2rem;
        }

        .hero-card {
            margin-top: 1.5rem;
        }

        body, .stApp {
            background: radial-gradient(circle at top left, #12294b 0%, #07111f 45%, #030711 100%);
            color: var(--text);
        }

        section[data-testid="stSidebar"] img {
            border-radius: 18px;
            border: 1px solid rgba(94, 234, 212, 0.26);
            box-shadow: 0 18px 36px rgba(6, 22, 60, 0.24);
        }

        .stSidebar {
            background: linear-gradient(180deg, rgba(8, 15, 32, 0.98) 0%, rgba(5, 11, 24, 0.98) 100%);
            border-right: 1px solid var(--border);
        }

        .hero-card {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(37, 99, 235, 0.72));
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 24px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 20px 45px rgba(2, 10, 27, 0.35);
        }

        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            color: white;
            margin-bottom: 6px;
        }

        .hero-subtitle {
            color: #dbeafe;
            font-size: 1rem;
        }

        .panel-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 16px 18px;
            backdrop-filter: blur(16px);
            box-shadow: 0 16px 35px rgba(2, 6, 23, 0.22);
        }

        .metric-card {
            background: linear-gradient(145deg, rgba(10, 22, 44, 0.95), rgba(13, 24, 44, 0.85));
            border: 1px solid rgba(96, 165, 250, 0.24);
            border-radius: 16px;
            padding: 16px;
            text-align: center;
            min-height: 112px;
        }

        .metric-value {
            font-size: 1.55rem;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 6px;
        }

        .metric-label {
            font-size: 0.9rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }

        .status-pill {
            display: inline-block;
            width: 100%;
            text-align: center;
            padding: 8px 10px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .status-online {
            background: rgba(34, 197, 94, 0.16);
            color: #bbf7d0;
            border: 1px solid rgba(34, 197, 94, 0.32);
        }

        .status-offline {
            background: rgba(248, 113, 113, 0.16);
            color: #fecaca;
            border: 1px solid rgba(248, 113, 113, 0.3);
        }

        .sidebar-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: white;
            margin-bottom: 8px;
        }

        .sidebar-subtext {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .section-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.5), transparent);
            margin: 14px 0 16px;
        }

        div[data-testid="stTabs"] button {
            border-radius: 999px;
            padding: 0.5rem 1rem;
            border: 1px solid rgba(96, 165, 250, 0.2);
            background: rgba(15, 23, 42, 0.74);
            color: var(--muted);
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: linear-gradient(135deg, rgba(96,165,250,0.35), rgba(94,234,212,0.24));
            color: white;
        }

        .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(96, 165, 250, 0.26);
            background: linear-gradient(135deg, rgba(96, 165, 250, 0.25), rgba(94, 234, 212, 0.2));
            color: white;
            transition: 0.2s ease;
        }

        .stButton > button:hover {
            border-color: rgba(94, 234, 212, 0.4);
            transform: translateY(-1px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "refresh_trigger" not in st.session_state:
    st.session_state.refresh_trigger = 0

bucket_name = os.getenv("BUCKET_NAME", "").strip()
region_name = os.getenv("AWS_REGION", "").strip()

with st.sidebar:
    logo_path = os.path.join("assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<div class='sidebar-title'>☁️ Cloud Vault</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-subtext'>A streamlined AWS S3 control center for uploads, storage insights, and object management.</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    s3_client = None
    connected = False
    connection_error = None

    aws_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

    has_creds = True
    if not aws_key or not aws_secret or not region_name or not bucket_name:
        has_creds = False
        connection_error = "Missing AWS configuration. Please set your .env values."

    if has_creds:
        try:
            s3_client = create_s3_client()
            verify_bucket_existence(s3_client, bucket_name)
            connected = True
        except Exception as e:
            connected = False
            connection_error = str(e)

    if connected:
        st.markdown('<div class="status-pill status-online">● Connected to AWS</div>', unsafe_allow_html=True)
        st.markdown(f"**Bucket:** `{bucket_name}`")
        st.markdown(f"**Region:** `{region_name}`")
    else:
        st.markdown('<div class="status-pill status-offline">● Disconnected</div>', unsafe_allow_html=True)
        if connection_error:
            st.error(connection_error)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    if st.button("Refresh Bucket Data", use_container_width=True, disabled=not connected):
        st.session_state.refresh_trigger += 1
        st.rerun()

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">Cloud Vault S3 Console</div>
        <div class="hero-subtitle">A polished workspace for uploading, browsing, and managing S3 objects with clarity and control.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner=False)
def load_bucket_data(trigger_val: int, _client: Any, bucket: str):
    if not _client or not bucket:
        return [], 0, 0
    try:
        files = list_files(_client, bucket)
        total_files, total_size = get_bucket_size(_client, bucket)
        return files, total_files, total_size
    except Exception as e:
        st.error(f"Failed to fetch S3 data: {str(e)}")
        return [], 0, 0

if not connected:
    st.markdown("""
    <div class="panel-card">
        <h3 style="margin-top:0;">Get connected in minutes</h3>
        <p style="color:#cbd5e1;">Add your AWS credentials and bucket settings to unlock the dashboard.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Quick setup guide", expanded=True):
        st.markdown(
            """
            1. Create or select an S3 bucket in the AWS console.
            2. Generate IAM access keys with S3 access permissions.
            3. Add the values to your .env file.
            4. Refresh the dashboard to connect.
            """
        )

    st.warning("Credentials are currently empty. Fill in the .env file to unlock AWS integration.")
    st.stop()

with st.spinner("Syncing bucket activity..."):
    all_files, total_files_count, total_size_bytes = load_bucket_data(
        st.session_state.refresh_trigger, s3_client, bucket_name
    )

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{total_files_count}</div>
            <div class="metric-label">Total Files</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{format_size(total_size_bytes)}</div>
            <div class="metric-label">Storage Used</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{bucket_name}</div>
            <div class="metric-label">Active Bucket</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

overview_tab, upload_tab, objects_tab, manage_tab = st.tabs(["Overview", "Upload", "Objects", "Download & Delete"])

with overview_tab:
    st.markdown("""
    <div class="panel-card">
        <h3 style="margin-top:0;">What this workspace does</h3>
        <p style="color:#cbd5e1;">Upload new assets, inspect current objects, and download or remove files without leaving this dashboard.</p>
    </div>
    """, unsafe_allow_html=True)

with upload_tab:
    st.markdown("### Upload a file")
    uploaded_file = st.file_uploader("Choose a file to upload directly to S3", key="file_upload_input")

    if uploaded_file is not None:
        filename = uploaded_file.name
        file_exists = filename in [f["Key"] for f in all_files]

        can_upload = True
        if file_exists:
            st.warning(f"A file named {filename} already exists in this bucket.")
            overwrite = st.checkbox("Overwrite the existing file", value=False, key="overwrite_status")
            if not overwrite:
                can_upload = False
                st.info("Enable overwrite to replace the existing object.")

        if can_upload:
            if st.button("Upload to S3", use_container_width=True):
                try:
                    with st.spinner(f"Uploading {filename} to AWS S3..."):
                        upload_file(s3_client, uploaded_file, filename, bucket_name)
                    st.success(f"{filename} was uploaded successfully.")
                    st.session_state.refresh_trigger += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")

with objects_tab:
    st.markdown("### Browse your bucket")

    if not all_files:
        st.info("Your S3 bucket is empty. Upload a file from the previous tab to see it appear here.")
    else:
        search_col, sort_col, order_col = st.columns([2, 1, 1])
        with search_col:
            search_query = st.text_input("Search by file name", "", placeholder="Type a name to filter...")
        with sort_col:
            sort_by = st.selectbox("Sort by", ["Name", "Size", "Date"])
        with order_col:
            sort_order = st.selectbox("Order", ["Ascending", "Descending"])

        filtered_files = [f for f in all_files if search_query.lower() in f["Key"].lower()]
        reverse_sort = sort_order == "Descending"
        if sort_by == "Name":
            filtered_files.sort(key=lambda x: x["Key"].lower(), reverse=reverse_sort)
        elif sort_by == "Size":
            filtered_files.sort(key=lambda x: x["Size"], reverse=reverse_sort)
        elif sort_by == "Date":
            filtered_files.sort(key=lambda x: x["LastModified"], reverse=reverse_sort)

        if not filtered_files:
            st.warning("No files match your current filter.")
        else:
            table_data = []
            for file in filtered_files:
                table_data.append(
                    {
                        "Type": get_file_icon(file["Key"]),
                        "File Name": file["Key"],
                        "Size": format_size(file["Size"]),
                        "Last Modified": file["LastModified"].strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            df = pd.DataFrame(table_data)
            st.dataframe(
                df,
                column_config={
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "File Name": st.column_config.TextColumn("File Name"),
                    "Size": st.column_config.TextColumn("Size"),
                    "Last Modified": st.column_config.TextColumn("Last Modified"),
                },
                hide_index=True,
                use_container_width=True,
            )

with manage_tab:
    st.markdown("### Download or remove objects")

    if not all_files:
        st.info("No objects are available to manage yet.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Download")
            file_names = [f["Key"] for f in all_files]
            selected_download = st.selectbox("Choose a file to download", options=file_names, key="download_selector")

            if selected_download:
                if st.button("Retrieve from S3", use_container_width=True):
                    try:
                        with st.spinner(f"Retrieving '{selected_download}' from S3..."):
                            file_bytes = download_file(s3_client, bucket_name, selected_download)
                        st.session_state.dl_bytes = file_bytes
                        st.session_state.dl_name = selected_download
                        st.success("File fetched successfully")
                    except Exception as e:
                        st.error(f"Retrieval failed: {str(e)}")

                if "dl_bytes" in st.session_state and st.session_state.dl_name == selected_download:
                    st.download_button(
                        label=f"Save '{selected_download}'",
                        data=st.session_state.dl_bytes,
                        file_name=st.session_state.dl_name,
                        mime="application/octet-stream",
                        use_container_width=True,
                    )

        with col_b:
            st.markdown("#### Delete")
            file_names = [f["Key"] for f in all_files]
            selected_delete = st.selectbox("Choose a file to delete", options=file_names, key="delete_selector")

            if selected_delete:
                confirm_key = f"confirm_del_{selected_delete}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if st.button("Delete Object", type="primary", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(f"Are you sure you want to permanently delete {selected_delete}?")
                    yes_btn, no_btn = st.columns(2)
                    with yes_btn:
                        if st.button("Yes, delete it", type="primary", use_container_width=True):
                            try:
                                with st.spinner("Deleting object..."):
                                    delete_file(s3_client, bucket_name, selected_delete)
                                st.success(f"{selected_delete} was deleted.")
                                st.session_state[confirm_key] = False
                                st.session_state.refresh_trigger += 1
                                st.rerun()
                            except Exception as e:
                                st.error(f"Deletion failed: {str(e)}")
                    with no_btn:
                        if st.button("Cancel", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
