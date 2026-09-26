"""Qrar (قرار) — AI Data Analyst for Power BI.

A Streamlit chat UI that turns natural-language questions into DAX queries
(via a local Ollama model or a cloud fallback), executes them against a
live Power BI Desktop model through the powerbi-modeling-mcp MCP server,
and renders the results as metrics, tables, or charts.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from core import ai_router, chat_store
from core.ai_router import AllProvidersFailedError
from core.mcp_client import MCPError
from core.powerbi import PowerBIConnector

st.set_page_config(page_title="قرار | Qrar", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .stChatMessage { border-radius: 12px; }
    section[data-testid="stSidebar"] { border-inline-end: 1px solid rgba(128,128,128,0.2); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_powerbi_connector() -> PowerBIConnector:
    """Single subprocess/MCP connection shared across reruns of this session.

    Without caching, every Streamlit rerun (which happens on each widget
    interaction) would spawn a brand-new powerbi-modeling-mcp.exe process.
    """
    return PowerBIConnector()


def _looks_chartable(df: pd.DataFrame) -> bool:
    numeric_cols = df.select_dtypes(include="number").columns
    return len(df.columns) == 2 and len(numeric_cols) >= 1 and len(df) > 1


def _build_chart(df: pd.DataFrame):
    numeric_cols = list(df.select_dtypes(include="number").columns)
    category_col = next((c for c in df.columns if c not in numeric_cols), df.columns[0])
    value_col = numeric_cols[0] if numeric_cols else df.columns[-1]
    return px.bar(df, x=category_col, y=value_col)


def _render_result(df: pd.DataFrame) -> None:
    if df.empty:
        return
    if len(df) == 1 and len(df.columns) == 1:
        st.metric(str(df.columns[0]), df.iloc[0, 0])
    else:
        st.dataframe(df, use_container_width=True)
        if _looks_chartable(df):
            st.plotly_chart(_build_chart(df), use_container_width=True)


def init_session_state() -> None:
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = chat_store.new_chat_id()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "schema" not in st.session_state:
        st.session_state.schema = None


init_session_state()
connector = get_powerbi_connector()

with st.sidebar:
    if config.LOGO_PATH.exists():
        st.image(str(config.LOGO_PATH), width=120)
    st.title("قرار — Qrar")
    st.caption("مساعدك الذكي لتحليل بيانات Power BI")

    if st.button("➕ محادثة جديدة", use_container_width=True):
        st.session_state.chat_id = chat_store.new_chat_id()
        st.session_state.messages = []
        st.rerun()

    st.subheader("المحادثات السابقة")
    for chat in chat_store.list_chats():
        label = chat["title"] or "محادثة بدون عنوان"
        if st.button(label, key=f"chat_{chat['id']}", use_container_width=True):
            loaded = chat_store.load_chat(chat["id"])
            st.session_state.chat_id = chat["id"]
            st.session_state.messages = loaded["messages"]
            st.rerun()

    st.divider()
    st.subheader("حالة الاتصال")
    if st.button("🔄 تحديث مخطط البيانات (Schema)", use_container_width=True):
        try:
            with st.spinner("جاري الاتصال بـ Power BI..."):
                st.session_state.schema = connector.get_schema()
            st.success("تم تحديث المخطط بنجاح")
        except MCPError as exc:
            st.error(f"تعذّر الاتصال بـ Power BI: {exc}")

    st.caption("ترتيب مزودي الذكاء الاصطناعي (Smart Fallback):")
    st.caption(" → ".join(config.PROVIDER_ORDER))

st.title("💬 اسأل بياناتك")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("dax"):
            with st.expander("عرض استعلام DAX"):
                st.code(message["dax"], language="sql")
        if message.get("table"):
            _render_result(pd.DataFrame(message["table"]))

question = st.chat_input("اكتب سؤالك عن بياناتك...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        assistant_message = {"role": "assistant", "content": ""}
        with st.spinner("جاري التحليل..."):
            try:
                if st.session_state.schema is None:
                    st.session_state.schema = connector.get_schema()

                result, provider_used = ai_router.generate_dax(
                    st.session_state.schema, question, st.session_state.messages
                )
                dax_query = result["dax"]
                explanation = result.get("explanation", "تم تنفيذ الاستعلام بنجاح.")

                data = connector.execute_dax(dax_query)
                rows = data.get("rows") or data.get("data") or []
                df = pd.DataFrame(rows)

                st.markdown(explanation)
                st.caption(f"تمت الإجابة بواسطة: {provider_used}")
                with st.expander("عرض استعلام DAX"):
                    st.code(dax_query, language="sql")
                _render_result(df)

                assistant_message = {
                    "role": "assistant",
                    "content": explanation,
                    "dax": dax_query,
                    "table": df.to_dict(orient="records"),
                }
            except AllProvidersFailedError as exc:
                answer = f"فشلت كل مزودات الذكاء الاصطناعي: {exc}"
                st.error(answer)
                assistant_message = {"role": "assistant", "content": answer}
            except MCPError as exc:
                answer = f"تعذّر تنفيذ الاستعلام في Power BI: {exc}"
                st.error(answer)
                assistant_message = {"role": "assistant", "content": answer}

    st.session_state.messages.append(assistant_message)
    title = st.session_state.messages[0]["content"][:40]
    chat_store.save_chat(st.session_state.chat_id, title, st.session_state.messages)
