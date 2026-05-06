import streamlit as st
import requests
import time
import os
from supabase import create_client, Client

# ==========================================
# 1. 配置与环境初始化 (UI 注入与风格统一)
# ==========================================
st.set_page_config(page_title="NAL | 视觉叙事深度评审引擎", page_icon="🏛️", layout="wide")

# 注入 CSS 以确保风格与 nal-ai.org 高度统一
st.markdown("""
    <style>
    /* 隐藏 Streamlit 默认页眉页脚，提升专业感 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 统一背景色与学术感字体 */
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, p, span, div {
        font-family: 'Georgia', 'Times New Roman', serif !important;
    }
    
    /* 优化报告边框的呈现效果 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 环境变量获取与安全校验 (核心改进)
# ==========================================
# 🚨 警告：切勿在此处写死真实的密钥！请确保在 Render 的 Environment 标签页中配置了它们。
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://pb-api.nal-ai.org")

# 平台自检：如果环境变量未注入，拦截运行并报错，防止发生意料之外的崩溃
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ 系统环境未就绪：缺少数据库或存储桶连接凭证。请联系 NAL 平台管理员在后台注入环境变量。")
    st.stop()

# 初始化 Supabase 客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 3. 页面头部与信息区
# ==========================================
st.title("🏛️ NAL 视觉协同评审引擎")
st.markdown("欢迎来到 **NewArtLiterature Collective** 数字化中枢。请上传您的视觉叙事素材，v65 引擎将结合您的创作意图，提供多维度的学术级评审。")

# ==========================================
# 4. 交互表单区
# ==========================================
with st.form("nal_evaluation_form"):
    user_intent = st.text_area(
        "📝 创作意图 / 核心表达 (选填)", 
        placeholder="请简述您在画面中试图传达的情感、故事背景或艺术设定...",
        height=100
    )
    
    uploaded_file = st.file_uploader(
        "🖼️ 上传视觉素材 (支持 JPG, PNG)", 
        type=["jpg", "jpeg", "png"]
    )
    
    submit_button = st.form_submit_button("🚀 提交 NAL 学术评审", use_container_width=True)

# ==========================================
# 5. 核心处理逻辑区 (上传与 API 协同)
# ==========================================
if submit_button:
    if not uploaded_file:
        st.warning("⚠️ 请先上传一张视觉素材。")
    else:
        try:
            # --- A. 上传图片到 Supabase 存储桶 ---
            file_bytes = uploaded_file.getvalue()
            file_ext = uploaded_file.name.split(".")[-1]
            file_name = f"review_{int(time.time())}.{file_ext}"
            
            # 执行上传 (假设你的 bucket 名字叫 images，请根据实际情况修改)
            bucket_name = "images" 
            res = supabase.storage.from_(bucket_name).upload(file_name, file_bytes)
            
            # 获取图片公开访问链接
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            
            # --- B. 组装发给后端的 Payload ---
            payload = {
                "image_url": public_url,
                "intent": user_intent
            }
            
            st.success("✅ 素材已加密上传至 NAL 云端，正在唤醒 v65 评审引擎...")
            
            # UI 占位符：进度条与状态提示
            progress_bar = st.progress(0)
            status_area = st.empty()
            start_time = time.time()
            quotes = [
                "正在解析画面构图与色彩张力...",
                "正在将视觉元素与您的创作意图进行对齐...",
                "正在调用 4:3:3 权重评价体系...",
                "正在撰写学术级评审报告，请稍候..."
            ]
            
            # --- C. 发起后端评审请求 ---
            resp = requests.post(f"{API_BASE_URL}/PB/api/evaluate", json=payload, timeout=30)
            
            if resp.status_code == 200:
                resp_data = resp.json()
                row_id = resp_data.get("row_id") # 假设后端立即返回任务 ID
                
                # --- D. 轮询等待结果 ---
                while True:
                    # 假设后端有一个查询状态的接口
                    status_resp = requests.get(f"{API_BASE_URL}/PB/api/status/{row_id}", timeout=10)
                    
                    try:
                        # 增加容错：防止后端返回非 JSON 格式的错误网页导致崩溃
                        data = status_resp.json()
                    except ValueError:
                        st.error("❌ 后端返回了无法解析的异常数据，可能网关出现了问题。")
                        break
                        
                    status = data.get("status")
                    
                    if status == "completed":
                        progress_bar.progress(100)
                        status_area.success(f"🎉 NAL 评审立项成功！档案 ID: {row_id}")
                        
                        report_text = data.get("v65_synergy_report", "报告提取失败。")
                        score = data.get("score", "N/A")
                        
                        # 使用 st.markdown 渲染具有排版格式的学术报告 (核心改进)
                        st.subheader("📑 V65 协同评审报告")
                        with st.container(border=True):
                            st.markdown(f"**综合学术评分:** `{score}`")
                            st.divider()
                            st.markdown(report_text)
                            
                        # 提供纯文本下载
                        st.download_button(
                            label="📥 下载学术评审报告",
                            data=f"NAL 评审报告 (ID: {row_id})\n综合得分: {score}\n\n{report_text}",
                            file_name=f"NAL_Report_{row_id}.txt",
                            mime="text/plain"
                        )
                        break
                        
                    elif status == "failed":
                        progress_bar.empty()
                        status_area.error("❌ 模型分析崩溃，请检查素材是否触碰安全限制或后端日志报错。")
                        break
                        
                    else:
                        # 正在处理中，更新伪进度条
                        elapsed = int(time.time() - start_time)
                        q_idx = (elapsed // 8) % len(quotes)
                        status_area.info(f"⏳ {quotes[q_idx]} (已耗时 {elapsed}s)")
                        progress_bar.progress(min(elapsed * 2, 95)) 
                        
                    time.sleep(5)
                    
            else:
                st.error(f"❌ 后端 API 拒绝服务 (HTTP {resp.status_code})")
                st.write(f"详细信息: {resp.text}")

        except Exception as e:
            st.error(f"📡 网络阻断或执行异常，无法连接到 NAL 评审中枢: {str(e)}")

# ==========================================
# 6. 页脚版权声明
# ==========================================
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "© 2026 NewArtLiterature Collective | 倡导数字时代的视觉先锋叙事"
    "</div>", 
    unsafe_allow_html=True
)
