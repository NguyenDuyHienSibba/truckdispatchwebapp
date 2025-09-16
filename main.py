import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from gtts import gTTS
import io
import re
# python -m streamlit run main.py

# === Cấu hình layout ===
st.set_page_config(layout="wide")
st.title("📋 TRUCK COORDINATING WEB APP")

# === 1. Khởi tạo client (cache lâu dài) ===
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# === 2. Tải dữ liệu Google Sheet với tùy chọn "refresh" ===
@st.cache_data(ttl=300, show_spinner="🔄 Đang tải dữ liệu...")
def load_data_cached():
    return load_data_raw()

def load_data_raw():
    client = get_gspread_client()
    sheet = client.open("ĐĂNG KÝ TÀI BXLVK ").worksheet("Bảng tài WH-Safety 2025")
    raw = sheet.get_all_values()
    headers = raw[0]
    rows = raw[1:]
    rows.reverse()
    df = pd.DataFrame(rows, columns=headers)

    # Lọc: chỉ giữ hàng có giá trị ở cột 'Giờ Vào Kho' (chỉnh lại tên nếu cần)
    df = df[df['Giờ Vào Kho'].astype(str).str.strip() != ""]
    return df

# === 3. Nút làm mới dữ liệu ===
refresh = st.button("🔁 Làm mới dữ liệu ngay")

if refresh:
    df = load_data_raw()  # bypass cache
    st.toast("✅ Dữ liệu đã được làm mới.")
else:
    df = load_data_cached()

# === 4. Tính năng phát thông báo nhanh ===
mau_thong_bao = [
    "Yêu cầu tài xế di chuyển vào khu vực chờ, giữ khoảng cách an toàn với xe nâng. ",
    "Mời xe di chuyển nhanh chóng vào kho. "
]

st.subheader("📢 Phát thông báo nhanh")

col1, col2 = st.columns([3, 1])

with col1:
    thong_bao_chon = st.selectbox(
        "Chọn mẫu thông báo:",
        options=["-- Nhập tay --"] + mau_thong_bao
    )
    if thong_bao_chon == "-- Nhập tay --":
        thong_bao_text = st.text_input("Nhập nội dung thông báo")
    else:
        thong_bao_text = thong_bao_chon

with col2:
    so_lan_phat = st.number_input("Số lần lặp", min_value=1, max_value=10, value=3)

if st.button("🔊 Phát thông báo nhanh"):
    if thong_bao_text.strip():
        thong_bao_gop = (". "*3).join([thong_bao_text] * so_lan_phat)
        tts = gTTS(text=thong_bao_gop, lang='vi')
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format='audio/mp3', autoplay=True)
        st.success(f"📢 {thong_bao_gop}")
    else:
        st.warning("Vui lòng chọn hoặc nhập nội dung thông báo!")

st.markdown("---")

# === 5. Danh sách kho cố định ===
kho_options = ['Kho D','Kho D, kế kho E','Kho E, kế kho D', 'Kho E, kế kho F', 'Kho F, kế kho E', 'Kho F, kế kho G', 'G']

# === 6. Khởi tạo session_state ===
st.session_state.setdefault('page', 0)
st.session_state.setdefault('selected_row', None)
st.session_state.setdefault('selected_kho', None)

# === 7. Pagination ===
rows_per_page = 10
total_pages = (len(df) + rows_per_page - 1) // rows_per_page

col_prev, _, col_next = st.columns([4, 1, 4])
with col_prev:
    if st.button("« Previous") and st.session_state.page > 0:
        st.session_state.page -= 1
with col_next:
    if st.button("Next »") and st.session_state.page < total_pages - 1:
        st.session_state.page += 1

st.caption(f"Page {st.session_state.page + 1} / {total_pages}")

start = st.session_state.page * rows_per_page
df_page = df.iloc[start: start + rows_per_page]

# === 8. Hiển thị danh sách và phát âm thanh tại chỗ ===
for i, (idx, row) in enumerate(df_page.iterrows()):
    actual_idx = start + i
    row_key = re.sub(r'\W+', '_', str(row['Biển Số Xe']))

    c1, c2, c3 = st.columns([3, 3, 1])

    with c1:
        st.markdown(f"**🚚 Biển số xe:** {row['Biển Số Xe']}")
    with c2:
        selected = st.selectbox(
            "Kho",
            kho_options,
            index=kho_options.index(row.get('Kho')) if row.get('Kho') in kho_options else 0,
            key=f"kho_{actual_idx}_{row_key}"
        )
    with c3:
        if st.button("🔊 Play", key=f"play_{actual_idx}_{row_key}"):
            st.session_state.selected_row = actual_idx
            st.session_state.selected_kho = selected

    if (
        st.session_state.selected_row == actual_idx and
        st.session_state.selected_kho == selected
    ):
        bien_so = str(row['Biển Số Xe'])
        five_digits = bien_so[-5:]
        digits = ''.join(re.findall(r'\d', five_digits))
        spoken_digits = ' '.join(digits)

        spoken_text = f"Mời xe {spoken_digits} vào {selected}. Xin nhắc lại, mời xe {spoken_digits} vào {selected}."
        written_text = f"Mời xe {bien_so} vào {selected}. Xin nhắc lại, mời xe {bien_so} vào {selected}."
        st.markdown("#### 🔊 Đang phát thông báo")
        st.success(f"📢 {written_text}")

        tts = gTTS(text=spoken_text, lang='vi')
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format='audio/mp3', autoplay=True)

        if st.button("Đóng thông báo", key=f"close_{actual_idx}_{row_key}"):
            st.session_state.selected_row = None
            st.session_state.selected_kho = None