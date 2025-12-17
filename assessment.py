# 安装命令：pip install streamlit pandas openpyxl
# 可选：pip install python-docx (如果要从 questions.doc 生成题库)
# 运行命令：streamlit run assessment.py

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import random

# 尝试导入 docx，如果没有安装则设为 None
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    Document = None

import os

# 配置
QUESTIONS_FILE = Path("questions.xlsx")
RESULTS_FILE = Path("results.xlsx")
CONFIG_FILE = Path("config.py")

# 加载或初始化管理员密码
if CONFIG_FILE.exists():
    try:
        import config
        ADMIN_PASSWORD = config.ADMIN_PASSWORD
    except:
        ADMIN_PASSWORD = "admin123"
else:
    ADMIN_PASSWORD = "admin123"

def save_admin_password(new_password):
    """保存管理员密码"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(f'ADMIN_PASSWORD = "{new_password}"')
    global ADMIN_PASSWORD
    ADMIN_PASSWORD = new_password

# 题库列表
BANK_NAMES = ["题库一", "题库二", "题库三"]

st.set_page_config(page_title="企业员工面试测评系统", page_icon="🧭", layout="wide")

# 自定义CSS样式
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        color: white;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    [data-testid="stSidebar"] label {
        color: white !important;
    }
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
    }
    [data-testid="stSidebar"] p {
        color: rgba(255, 255, 255, 0.9) !important;
    }
    .sidebar-title {
        color: white;
        font-size: 24px;
        font-weight: bold;
        padding: 20px 0;
        text-align: center;
    }
    .sidebar-section {
        background: rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def parse_questions_from_doc(doc_path: Path, bank_name: str) -> list:
    """
    从 doc 文件解析题目
    一级标题 -> 题目
    二级标题 -> 选项（A/B/C/D）
    返回格式：题目字典列表
    """
    if not HAS_DOCX:
        return []
    
    if not doc_path.exists():
        return []
    
    try:
        doc = Document(str(doc_path))
        questions = []
        current_question = None
        option_count = 0
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            style_name = para.style.name if para.style else ""
            
            # 一级标题作为题目
            if style_name.startswith('Heading 1') or (len(text) > 10 and not text.startswith(('A.', 'B.', 'C.', 'D.', 'A、', 'B、', 'C、', 'D、'))):
                # 如果有之前的题目未完成，先保存
                if current_question and option_count >= 4:
                    questions.append(current_question)
                
                # 创建新题目
                current_question = {
                    'ID': len(questions) + 1,
                    'Bank': bank_name,
                    'Question': text,
                    'Option_A': '',
                    'Score_A': 0,
                    'Option_B': '',
                    'Score_B': 0,
                    'Option_C': '',
                    'Score_C': 0,
                    'Option_D': '',
                    'Score_D': 0,
                }
                option_count = 0
            
            # 二级标题或选项格式（A. B. C. D.）
            elif style_name.startswith('Heading 2') or re.match(r'^[A-D][\.、]\s*', text):
                if current_question:
                    # 提取选项文本和分数
                    match = re.match(r'^([A-D])[\.、]\s*(.+?)(?:（(\d+)分）|\((\d+)分\)|（(\d+)）|\((\d+)\))?\s*$', text)
                    if match:
                        option_letter = match.group(1)
                        option_text = match.group(2).strip()
                        score = 0
                        # 提取分数
                        for i in range(3, 8):
                            if match.group(i):
                                try:
                                    score = int(match.group(i))
                                    break
                                except:
                                    pass
                        
                        if option_letter in ['A', 'B', 'C', 'D']:
                            current_question[f'Option_{option_letter}'] = option_text
                            current_question[f'Score_{option_letter}'] = score
                            option_count += 1
        
        # 保存最后一个题目
        if current_question and option_count >= 4:
            questions.append(current_question)
        
        return questions
    except Exception as e:
        st.error(f"解析文档时出错: {e}")
        return []


def init_db():
    """初始化题库和结果文件"""
    # 如果存在 questions.doc，尝试从文档生成题库
    doc_path = Path("questions.doc")
    if not doc_path.exists():
        doc_path = Path("questions.docx")
    
    if doc_path.exists() and HAS_DOCX and not QUESTIONS_FILE.exists():
        st.info("正在从文档文件生成题库...")
        
        with pd.ExcelWriter(QUESTIONS_FILE, engine='openpyxl') as writer:
            for bank_name in BANK_NAMES:
                questions = parse_questions_from_doc(doc_path, bank_name)
                
                if questions:
                    df = pd.DataFrame(questions)
                    df = df[['ID', 'Bank', 'Question', 'Option_A', 'Score_A', 
                            'Option_B', 'Score_B', 'Option_C', 'Score_C', 
                            'Option_D', 'Score_D']]
                    df.to_excel(writer, sheet_name=bank_name, index=False)
                else:
                    # 如果解析失败，创建默认10道题目
                    create_default_questions_for_bank(writer, bank_name)
        
        st.success("已从文档文件生成题库")
    elif not QUESTIONS_FILE.exists():
        # 创建默认题库
        with pd.ExcelWriter(QUESTIONS_FILE, engine='openpyxl') as writer:
            for bank_name in BANK_NAMES:
                create_default_questions_for_bank(writer, bank_name)
    
    # 初始化结果文件
    if not RESULTS_FILE.exists():
        pd.DataFrame(
            columns=["Timestamp", "Name", "Phone", "Total_Score", "Details", "Bank"]
        ).to_excel(RESULTS_FILE, index=False)


def create_default_questions_for_bank(writer, bank_name: str):
    """为指定题库创建10道默认题目"""
    base_questions = [
        {
            "Question": "你如何评估并选择合适的技术方案？",
            "Option_A": "调研多种方案并基于指标对比",
            "Score_A": 5,
            "Option_B": "使用熟悉的方案，减少尝试",
            "Score_B": 3,
            "Option_C": "跟随团队已有方案",
            "Score_C": 2,
            "Option_D": "直接使用网络上找到的示例",
            "Score_D": 1,
        },
        {
            "Question": "当团队产生分歧时，你的处理方式？",
            "Option_A": "组织复盘，聚焦事实与共识",
            "Score_A": 5,
            "Option_B": "请主管拍板",
            "Score_B": 3,
            "Option_C": "回避争议，先做自己能做的",
            "Score_C": 2,
            "Option_D": "保持中立，不参与讨论",
            "Score_D": 1,
        },
        {
            "Question": "面对模糊需求，你会怎么做？",
            "Option_A": "拆解假设，快速验证并迭代",
            "Score_A": 5,
            "Option_B": "等待完整需求文档",
            "Score_B": 3,
            "Option_C": "按类似需求直接复用方案",
            "Score_C": 2,
            "Option_D": "暂缓推进，优先其他任务",
            "Score_D": 1,
        },
        {
            "Question": "你如何确保代码质量？",
            "Option_A": "单测+代码评审+持续集成",
            "Score_A": 5,
            "Option_B": "主要依赖手工自测",
            "Score_B": 3,
            "Option_C": "上线后根据反馈修复",
            "Score_C": 2,
            "Option_D": "简单跑通即可",
            "Score_D": 1,
        },
        {
            "Question": "遇到跨团队协作阻塞时？",
            "Option_A": "主动拉齐目标与时间表，持续跟进",
            "Score_A": 5,
            "Option_B": "等待对方反馈",
            "Score_B": 3,
            "Option_C": "只完成自己部分",
            "Score_C": 2,
            "Option_D": "放缓节奏，降低优先级",
            "Score_D": 1,
        },
    ]
    
    # 生成10道题目（重复使用base题目）
    questions = []
    for i in range(10):
        base_q = base_questions[i % len(base_questions)].copy()
        base_q['ID'] = i + 1
        base_q['Bank'] = bank_name
        questions.append(base_q)
    
    df = pd.DataFrame(questions)
    df = df[['ID', 'Bank', 'Question', 'Option_A', 'Score_A', 
            'Option_B', 'Score_B', 'Option_C', 'Score_C', 
            'Option_D', 'Score_D']]
    df.to_excel(writer, sheet_name=bank_name, index=False)


@st.cache_data
def load_questions(bank_name: str = None) -> pd.DataFrame:
    """加载指定题库或所有题库"""
    
    def normalize_df(df, bank):
        """将新版Excel格式转换为系统内部格式"""
        # 检查是否为新格式（包含"题目"列）
        if "题目" in df.columns:
            new_rows = []
            for idx, row in df.iterrows():
                new_row = {
                    "ID": idx + 1,
                    "Bank": bank,
                    "Question": row["题目"],
                    "Option_A": row.get("选项1", ""),
                    "Score_A": row.get("分值1", 0),
                    "Option_B": row.get("选项2", ""),
                    "Score_B": row.get("分值2", 0),
                    "Option_C": row.get("选项3", ""),
                    "Score_C": row.get("分值3", 0),
                    "Option_D": row.get("选项4", ""),
                    "Score_D": row.get("分值4", 0),
                }
                new_rows.append(new_row)
            return pd.DataFrame(new_rows)
        return df

    if bank_name:
        try:
            df = pd.read_excel(QUESTIONS_FILE, sheet_name=bank_name)
            return normalize_df(df, bank_name)
        except:
            return pd.DataFrame()
    else:
        # 加载所有题库
        all_questions = []
        # 获取Excel中所有的Sheet名
        try:
            xl = pd.ExcelFile(QUESTIONS_FILE)
            sheet_names = xl.sheet_names
        except:
            sheet_names = BANK_NAMES

        for bank in sheet_names:
            try:
                df = pd.read_excel(QUESTIONS_FILE, sheet_name=bank)
                df = normalize_df(df, bank)
                if not df.empty:
                    # 确保ID列存在
                    if 'ID' not in df.columns:
                        df['ID'] = range(1, len(df) + 1)
                    if 'Bank' not in df.columns:
                        df['Bank'] = bank
                    all_questions.append(df)
            except:
                continue
        if all_questions:
            return pd.concat(all_questions, ignore_index=True)
        return pd.DataFrame()


def save_questions(df: pd.DataFrame, bank_name: str):
    """保存题库到指定sheet"""
    # 读取现有的所有sheet
    existing_data = {}
    for bank in BANK_NAMES:
        try:
            existing_data[bank] = pd.read_excel(QUESTIONS_FILE, sheet_name=bank)
        except:
            existing_data[bank] = pd.DataFrame()
    
    # 更新当前题库
    existing_data[bank_name] = df
    
    # 保存所有sheet
    with pd.ExcelWriter(QUESTIONS_FILE, engine='openpyxl') as writer:
        for bank, bank_df in existing_data.items():
            bank_df.to_excel(writer, sheet_name=bank, index=False)


def load_results() -> pd.DataFrame:
    """加载结果数据"""
    if RESULTS_FILE.exists():
        return pd.read_excel(RESULTS_FILE)
    return pd.DataFrame(columns=["Timestamp", "Name", "Phone", "Total_Score", "Details", "Bank"])


def save_result(new_row: dict):
    """保存考试结果"""
    df_res = load_results()
    df_res = pd.concat([df_res, pd.DataFrame([new_row])], ignore_index=True)
    df_res.to_excel(RESULTS_FILE, index=False)


def candidate_view():
    """候选人视图 - 随机展示题目"""
    st.header("🎯 候选人测评")
    st.write("请完成以下信息并作答。")

    name = st.text_input("姓名 (必填)", key="candidate_name")
    phone = st.text_input("手机号 (必填)", key="candidate_phone")

    # 随机选择一个题库
    if not 'selected_bank_seed' in st.session_state:
        # 获取所有可用的题库名称
        try:
            xl = pd.ExcelFile(QUESTIONS_FILE)
            available_banks = xl.sheet_names
        except:
            available_banks = BANK_NAMES
            
        if available_banks:
            st.session_state.selected_bank_seed = random.choice(available_banks)
        else:
            st.session_state.selected_bank_seed = BANK_NAMES[0]
    
    selected_bank = st.session_state.selected_bank_seed
    
    # 加载该题库所有题目
    questions_list = load_questions(selected_bank)
    
    if questions_list.empty:
        st.error("题库为空，请联系管理员。")
        return
    
    # 随机打乱题目顺序
    # 使用 session_state 保持题目顺序，避免交互时刷新
    if 'shuffled_questions' not in st.session_state or st.session_state.current_bank != selected_bank:
        st.session_state.shuffled_questions = questions_list.sample(frac=1).reset_index(drop=True)
        st.session_state.current_bank = selected_bank
        
    questions_list = st.session_state.shuffled_questions
    
    st.divider()
    st.subheader("请完成以下题目：")
    
    answers = {}
    
    # 显示所有题目（随机顺序）
    for idx, row in questions_list.iterrows():
        qid = f"{row.get('Bank', '')}_{row['ID']}"  # 使用题库+ID作为唯一标识
        # bank = row.get("Bank", "未知题库") # 不再显示题库
        prompt = f"{idx + 1}. {row['Question']}"
        
        choice = st.radio(
            prompt,
            options=["A", "B", "C", "D"],
            format_func=lambda x, r=row: {
                "A": r["Option_A"],
                "B": r["Option_B"],
                "C": r["Option_C"],
                "D": r["Option_D"],
            }[x],
            key=f"q_{qid}_{idx}",
        )
        answers[qid] = choice
        st.divider()

    if st.button("提交", type="primary", use_container_width=True):
        if not name.strip() or not phone.strip():
            st.warning("姓名和手机号为必填项。")
            return

        # 计算总分 - 通过索引匹配
        total_score = 0
        bank_scores = {}
        
        # 使用索引来匹配答案和题目
        answer_list = list(answers.items())
        for idx, (qid_key, choice) in enumerate(answer_list):
            if idx < len(questions_list):
                row = questions_list.iloc[idx]
                score = row[f"Score_{choice}"]
                total_score += score
                
                bank = row.get("Bank", "未知")
                if bank not in bank_scores:
                    bank_scores[bank] = 0
                bank_scores[bank] += score

        new_row = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Name": name.strip(),
            "Phone": phone.strip(),
            "Total_Score": total_score,
            "Details": str(bank_scores),
            "Bank": ", ".join(bank_scores.keys()),
        }
        save_result(new_row)
        st.success("提交成功，请等待通知。")
        st.balloons()


def admin_view():
    """管理员视图"""
    st.header("🛠️ 管理员后台")
    
    # 题库选择
    selected_bank = st.selectbox("选择要管理的题库", BANK_NAMES, key="bank_selector")
    
    # 加载选中的题库
    df_q = load_questions(selected_bank)
    
    if df_q.empty:
        st.warning(f"题库 '{selected_bank}' 为空，请添加题目。")
        df_q = pd.DataFrame(columns=['ID', 'Bank', 'Question', 'Option_A', 'Score_A', 
                                     'Option_B', 'Score_B', 'Option_C', 'Score_C', 
                                     'Option_D', 'Score_D'])
        df_q['Bank'] = selected_bank

    st.subheader(f"📚 {selected_bank} 管理")
    
    # 题库管理
    edited_df = st.data_editor(
        df_q,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"questions_editor_{selected_bank}",
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Bank": st.column_config.TextColumn("题库", disabled=True),
            "Question": st.column_config.TextColumn("问题"),
            "Option_A": st.column_config.TextColumn("选项A"),
            "Score_A": st.column_config.NumberColumn("分数A", width="small"),
            "Option_B": st.column_config.TextColumn("选项B"),
            "Score_B": st.column_config.NumberColumn("分数B", width="small"),
            "Option_C": st.column_config.TextColumn("选项C"),
            "Score_C": st.column_config.NumberColumn("分数C", width="small"),
            "Option_D": st.column_config.TextColumn("选项D"),
            "Score_D": st.column_config.NumberColumn("分数D", width="small"),
        }
    )
    
    # 确保Bank列正确
    if 'Bank' not in edited_df.columns or edited_df['Bank'].isna().any():
        edited_df['Bank'] = selected_bank
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存修改", type="primary", use_container_width=True):
            # 重新编号ID
            edited_df['ID'] = range(1, len(edited_df) + 1)
            save_questions(edited_df, selected_bank)
            st.success(f"题库 '{selected_bank}' 已保存")
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("🔄 重新加载", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # 系统设置（修改密码）
    with st.expander("⚙️ 系统设置"):
        st.subheader("修改管理员密码")
        new_pass = st.text_input("新密码", type="password", key="new_admin_pass")
        confirm_pass = st.text_input("确认新密码", type="password", key="confirm_admin_pass")
        
        if st.button("更新密码"):
            if not new_pass:
                st.error("密码不能为空")
            elif new_pass != confirm_pass:
                st.error("两次输入的密码不一致")
            else:
                save_admin_password(new_pass)
                st.success("管理员密码已更新，请重新登录")
                st.rerun()

    # 成绩报表
    st.subheader("📊 成绩报表")
    df_res = load_results()
    
    if len(df_res) > 0:
        # 显示数据编辑器，允许删除行
        edited_res = st.data_editor(
            df_res,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="results_editor",
            column_config={
                "Timestamp": st.column_config.TextColumn("提交时间", disabled=True),
                "Name": st.column_config.TextColumn("姓名", disabled=True),
                "Phone": st.column_config.TextColumn("手机号", disabled=True),
                "Total_Score": st.column_config.NumberColumn("总分", disabled=True),
                "Details": st.column_config.TextColumn("得分详情", disabled=True),
                "Bank": st.column_config.TextColumn("所属题库", disabled=True),
            }
        )
        
        # 检查是否有数据变动（删除）
        if len(edited_res) != len(df_res):
            if st.button("💾 保存成绩变动", type="primary"):
                try:
                    edited_res.to_excel(RESULTS_FILE, index=False)
                    st.success("成绩记录已更新")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败，请检查文件是否被占用: {e}")
        
        col1, col2 = st.columns(2)
        with col1:
            csv_data = edited_res.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "📥 下载成绩 CSV",
                data=csv_data,
                file_name=f"results_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col2:
            if st.button("🗑️ 清空所有记录", use_container_width=True):
                if st.session_state.get('confirm_clear') != True:
                    st.session_state.confirm_clear = True
                    st.warning("确定要清空所有成绩吗？再次点击按钮确认。")
                else:
                    try:
                        pd.DataFrame(columns=["Timestamp", "Name", "Phone", "Total_Score", "Details", "Bank"]).to_excel(RESULTS_FILE, index=False)
                        st.session_state.confirm_clear = False
                        st.success("所有成绩已清空")
                        st.rerun()
                    except Exception as e:
                        st.error(f"清空失败: {e}")
    else:
        st.info("暂无考试结果")


def main():
    """主函数"""
    init_db()

    st.title("🏢 企业员工面试测评系统")

    # 美化的侧边栏
    with st.sidebar:
        st.markdown('<div class="sidebar-title">🎯 系统导航</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 👤 身份选择")
        role = st.radio(
            "请选择身份",
            ["候选人", "管理员"],
            key="role_selector",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if role == "管理员":
            st.markdown("### 🔐 权限验证")
            admin_pass = st.text_input(
                "管理员密码",
                type="password",
                key="admin_password",
                help="请输入管理员密码以访问后台"
            )
            is_admin = admin_pass == ADMIN_PASSWORD
        else:
            is_admin = False

    # 根据角色显示相应视图
    if role == "管理员":
        if not is_admin:
            st.error("❌ 管理员密码错误或未输入，无法访问后台。")
            st.info("💡 请在侧边栏输入正确的管理员密码")
            return
        admin_view()
    else:
        candidate_view()


if __name__ == "__main__":
    main()
