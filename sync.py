import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px


# ==========================================
# 1. KONFIGURASI WEBSITE
# ==========================================

st.set_page_config(
    page_title="SIM-PETANI SUMUT",
    page_icon="🌾",
    layout="wide"
)

st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}

[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. KONEKSI DATABASE DATA WAREHOUSE
# ==========================================

import os
import streamlit as st

def get_database_url():

    # 1. Prioritaskan environment variable GitHub Actions
    database_url = os.getenv("DATAWAREHOUSE_URL")

    if database_url:
        return database_url

    # 2. Jika dijalankan di Streamlit Cloud,
    # gunakan konfigurasi Streamlit Secrets
    try:
        return st.secrets["datawarehouse"]["url"]

    except Exception as e:
        raise RuntimeError(
            "Koneksi Data Warehouse belum dikonfigurasi. "
            "Tambahkan DATAWAREHOUSE_URL pada GitHub Actions "
            "atau [datawarehouse].url pada Streamlit Secrets."
        ) from e


def read_data(query, params=None):

    conn = None

    try:

        database_url = get_database_url()

        conn = psycopg2.connect(
            database_url,
            connect_timeout=20,
            sslmode="require",
            application_name="SIM_PETANI_SUMUT"
        )

        with conn.cursor() as cur:

            cur.execute(query, params)

            # Mendapatkan nama kolom
            columns = [
                description[0]
                for description in cur.description
            ]

            # Mengambil data
            rows = cur.fetchall()

            # Mengubah hasil menjadi Pandas DataFrame
            df = pd.DataFrame(
                rows,
                columns=columns
            )

        return df

    except psycopg2.Error as e:

        st.error(
            f"Database Error: {type(e).__name__}: {e}"
        )

        raise

    except Exception as e:

        st.error(
            f"Application Error: {type(e).__name__}: {e}"
        )

        raise

    finally:

        if conn is not None:
            conn.close()


# ==========================================
# 3. HEADER
# ==========================================

st.title("🌾 SIM-PETANI SUMATERA UTARA")

st.markdown("""
**Sistem Informasi Pemetaan Petani dan Penyuluh
Provinsi Sumatera Utara**

Government Agricultural Data Dashboard
""")

st.divider()
# ==========================================
# 4. AMBIL TANGGAL SNAPSHOT
# ==========================================

dates = read_data("""
    SELECT DISTINCT id_tanggal
    FROM dw.fact_petani_harian
    ORDER BY id_tanggal DESC
""")

if dates.empty:

    st.warning(
        "Belum terdapat data pada Data Warehouse."
    )

    st.stop()


date_options = dates["id_tanggal"].tolist()

selected_date = st.sidebar.selectbox(
    "Pilih Tanggal Snapshot",
    date_options
)


# ==========================================
# 5. SIDEBAR NAVIGASI
# ==========================================

menu = st.sidebar.radio(
    "MENU NAVIGASI",
    [
        "Dashboard Utama",
        "Statistik Kabupaten",
        "Statistik Komoditas",
        "Data Petani"
    ]
)


# ==========================================
# 6. DASHBOARD UTAMA
# ==========================================

if menu == "Dashboard Utama":

    summary = read_data("""
        SELECT
            COUNT(*) AS total_petani,
            COALESCE(SUM(luas_lahan), 0) AS total_luas,
            COUNT(DISTINCT wilayah_sumber) AS total_kabupaten,
            COUNT(DISTINCT id_komoditas) AS total_komoditas
        FROM dw.fact_petani_harian
        WHERE id_tanggal = %s
    """, (selected_date,))

    if summary.empty:
        st.warning("Data ringkasan tidak tersedia.")
        st.stop()

    r = summary.iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Petani",
        f"{int(r.total_petani):,}"
    )

    c2.metric(
        "Luas Lahan",
        f"{float(r.total_luas):,.2f} Ha"
    )

    c3.metric(
        "Kabupaten",
        int(r.total_kabupaten)
    )

    c4.metric(
        "Komoditas",
        int(r.total_komoditas)
    )

    st.subheader("Sebaran Petani per Kabupaten")

    df = read_data("""
        SELECT
            kabupaten,
            total_petani,
            total_luas_lahan
        FROM dw.vw_petani_kabupaten
        WHERE id_tanggal = %s
        ORDER BY total_petani DESC
    """, (selected_date,))

    if df.empty:

        st.info("Data statistik kabupaten belum tersedia.")

    else:

        col1, col2 = st.columns(2)

        with col1:

            fig = px.bar(
                df,
                x="kabupaten",
                y="total_petani",
                color="kabupaten",
                title="Jumlah Petani per Kabupaten",
                text="total_petani"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col2:
            search = st.text_input(
        "Cari kode petani atau desa"
    )

    if search and not df.empty:

        mask = (
            df["kode_petani"].astype(str).str.contains(
                search,
                case=False,
                na=False,
                regex=False
            )
            |
            df["desa"].astype(str).str.contains(
                search,
                case=False,
                na=False,
                regex=False
            )
        )

        df = df[mask]


    # --------------------------------------
    # 9.6 TAMPILKAN DATA
    # --------------------------------------

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------
    # 9.7 DOWNLOAD CSV
    # --------------------------------------

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="📥 Download Data CSV",
        data=csv,
        file_name="data_petani_sumut.csv",
        mime="text/csv"
    )


# ==========================================
# 10. FOOTER
# ==========================================

st.divider()

st.caption(
    "SIM-PETANI SUMUT | Data Warehouse Pertanian "
    "| Universitas Sumatera Utara"
)
