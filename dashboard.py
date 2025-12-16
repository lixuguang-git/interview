# 安装命令：pip install streamlit pandas openpyxl plotly
# 运行命令：streamlit run dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="销售数据仪表盘",
    page_icon="📊",
    layout="wide"
)

# 使用缓存加载数据
@st.cache_data
def load_data():
    """加载销售数据"""
    df = pd.read_excel('sales_data.xlsx')
    # 计算总销售额
    df['总销售额'] = df['单价'] * df['数量']
    # 确保销售日期是日期格式
    df['销售日期'] = pd.to_datetime(df['销售日期'])
    return df

# 加载数据
df = load_data()

# 侧边栏 - 部门筛选器
st.sidebar.header("🔍 数据筛选")

# 获取所有部门
all_departments = df['所属部门'].unique().tolist()

# 多选框，默认全选
selected_departments = st.sidebar.multiselect(
    "选择部门",
    options=all_departments,
    default=all_departments,
    key="department_filter"
)

# 如果没有选择任何部门，使用全部部门
if not selected_departments:
    selected_departments = all_departments

# 根据筛选条件过滤数据
filtered_df = df[df['所属部门'].isin(selected_departments)]

# 侧边栏 - 下载按钮
st.sidebar.divider()
st.sidebar.header("📥 数据导出")

# 将筛选后的数据转换为 CSV
csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')

# 下载按钮
st.sidebar.download_button(
    label="📥 下载当前数据",
    data=csv_data,
    file_name=f"sales_data_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    help="下载当前筛选后的数据为 CSV 文件"
)

# 页面标题
st.title("📊 销售数据仪表盘")

# 核心指标 (KPI Cards)
st.header("核心指标")

col1, col2, col3 = st.columns(3)

# 计算指标
total_sales = filtered_df['总销售额'].sum()
total_orders = len(filtered_df)
avg_order_value = filtered_df['总销售额'].mean() if total_orders > 0 else 0

# KPI 卡片 1：总销售额
with col1:
    st.metric(
        label="💰 总销售额",
        value=f"¥{total_sales:,.0f}",
        delta=None
    )

# KPI 卡片 2：总订单数
with col2:
    st.metric(
        label="📦 总订单数",
        value=f"{total_orders:,}",
        delta=None
    )

# KPI 卡片 3：平均客单价
with col3:
    st.metric(
        label="💵 平均客单价",
        value=f"¥{avg_order_value:,.2f}",
        delta=None
    )

st.divider()

# 交互式图表
st.header("数据可视化")

col1, col2 = st.columns(2)

# 图1：各部门销售额占比（饼图）
with col1:
    st.subheader("部门销售额占比")
    department_sales = filtered_df.groupby('所属部门')['总销售额'].sum().reset_index()
    
    fig_pie = px.pie(
        department_sales,
        values='总销售额',
        names='所属部门',
        title="各部门销售额占比",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

# 图2：每日销售趋势（折线图）
with col2:
    st.subheader("每日销售趋势")
    daily_sales = filtered_df.groupby('销售日期')['总销售额'].sum().reset_index()
    daily_sales = daily_sales.sort_values('销售日期')
    
    fig_line = px.line(
        daily_sales,
        x='销售日期',
        y='总销售额',
        title="销售趋势（按日期）",
        markers=True,
        color_discrete_sequence=['#1f77b4']
    )
    fig_line.update_layout(
        xaxis_title="日期",
        yaxis_title="销售额 (¥)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# 原始数据表格
st.header("原始数据")

# 复选框：是否显示原始数据
show_raw_data = st.checkbox("显示原始数据", value=False)

if show_raw_data:
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )
    
    # 下载按钮
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下载 CSV",
        data=csv,
        file_name=f"sales_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
