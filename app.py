import streamlit as st
import requests
import time
import os
from supabase import create_client, Client

# ==========================================
# 1. 配置与环境初始化 (保持学术纸张风格)
# ==========================================
st.set_page_config(page_title="NAL | 视觉叙事深度评审引擎", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, p, span, div { font-family: 'Georgia', 'Times New Roman', serif !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# 兼容 Render 与 Streamlit 环境的多重保险读取
def get_config(key, default=""):
    val = os.environ.get(key)
    if val: return val
    try: return st.secrets.get(key, default)
    except: return default

SUPABASE_URL = get_config("SUPABASE_URL")
SUPABASE_KEY = get_config("SUPABASE_KEY")
API_BASE_URL = get_config("API_BASE_URL", "https://pb-api.nal-ai.org")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ 系统环境未就绪：缺少数据库连接凭证。请联系 NAL 平台管理员。")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. 恢复：左侧边栏控制中枢 (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ 评审环境配置")
    
    # 恢复载体类型选择
    target_type = st.radio(
        "选择视觉载体类型",
        ["🎨 独立插画 (Single Illustration)", "📖 绘本跨页 (Picture Book Spread)"]
    )
    
    st.markdown("---")
    
    # 运行模式选择与动态引擎降级逻辑
    run_mode = st.selectbox(
        "系统运行模式", 
        ["Standard (标准生产)", "Open_test (内部测试)"]
    )
    
    # 根据内测需求自动切换底层核心
    engine_version = "gemini-2.5-flash" if "Open_test" in run_mode else "gemini-3.1-pro"
    
    st.info(f"💡 当前调用的视觉大模型核心:\n\n**{engine_version}**")
    
    st.divider()
    st.caption("NAL Collective © 2026")

# ==========================================
# 3. 主界面交互区
# ==========================================
st.title("🏛️ NAL 视觉协同评审引擎")
st.markdown("欢迎来到 **NewArtLiterature Collective** 数字化中枢。请配置左侧参数，并上传您的视觉叙事素材。")

with st.form("nal_evaluation_form"):
    user_intent = st.text_area(
        "📝 创作意图 / 核心表达 (选填)", 
        placeholder="请简述您在画面中试图传达的情感、故事背景或技术设定...",
        height=100
    )
    uploaded_file = st.file_uploader("🖼️ 上传视觉素材 (支持 JPG, PNG)", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button("🚀 提交 NAL 学术评审", use_container_width=True)

# ==========================================
# 4. 核心处理与安全通信逻辑
# ==========================================
if submit_button:
    if not uploaded_file:
        st.warning("⚠️ 请先上传一张视觉素材。")
    else:
        try:
            # A. 上传到 Supabase
            file_bytes = uploaded_file.getvalue()
            file_ext = uploaded_file.name.split(".")[-1]
            file_name = f"review_{int(time.time())}.{file_ext}"
            
            bucket_name = "images" # 请确保这是你真实的 bucket 名称
            supabase.storage.from_(bucket_name).upload(file_name, file_bytes)
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            
            # B. 组装发给后端的 Payload (加入了侧边栏的参数)
            payload = {
                "image_url": public_url,
                "intent": user_intent,
                "target_type": target_type,
                "engine": engine_version  # 将引擎版本传递给后端
            }
            
            st.success("✅ 素材已就绪，正在唤醒 v65 评审引擎...")
            progress_bar = st.progress(0)
            status_area = st.empty()
            start_time = time.time()
            quotes = ["解析画面构图...", "对齐创作意图...", "调用评价体系...", "撰写学术报告..."]
            
            # C. 发起 API 请求
            resp = requests.post(f"{API_BASE_URL}/PB/api/evaluate", json=payload, timeout=30)
            
            if resp.status_code == 200:
                row_id = resp.json().get("row_id")
                
                # D. 轮询状态
                while True:
                    status_resp = requests.get(f"{API_BASE_URL}/PB/api/status/{row_id}", timeout=10)
                    try:
                        data = status_resp.json()
                    except ValueError:
                        st.error("❌ 后端返回了异常格式数据，通信中断。")
                        break
                        
                    status = data.get("status")
                    
                    if status == "completed":
                        progress_bar.progress(100)
                        status_area.success(f"🎉 NAL 评审立项成功！档案 ID: {row_id}")
                        
                        report_text = data.get("v65_synergy_report", "报告提取失败。")
                        score = data.get("score", "N/A")
                        
                        st.subheader("📑 V65 协同评审报告")
                        with st.container(border=True):
                            st.markdown(f"**综合学术评分:** `{score}`")
                            st.divider()
                            st.markdown(report_text)
                        break
                        
                    elif status == "failed":
                        progress_bar.empty()
                        status_area.error("❌ 模型分析崩溃，请检查素材限制。")
                        break
                        
                    else:
                        elapsed = int(time.time() - start_time)
                        status_area.info(f"⏳ {quotes[(elapsed // 8) % len(quotes)]} (已耗时 {elapsed}s)")
                        progress_bar.progress(min(elapsed * 2, 95)) 
                        
                    time.sleep(5)
            else:
                st.error(f"❌ 后端 API 拒绝服务 (HTTP {resp.status_code})")
        except Exception as e:
            st.error(f"📡 网络阻断，无法连接到 NAL 评审中枢: {str(e)}")

# ==========================================
# 5. 底部版权
# ==========================================
st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>© 2026 NewArtLiterature Collective | 倡导数字时代的视觉先锋叙事</div>", unsafe_allow_html=True)
