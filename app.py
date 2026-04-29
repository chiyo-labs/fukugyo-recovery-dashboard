from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials


st.set_page_config(
    page_title="副業回収ダッシュボード",
    page_icon="💹",
    layout="wide",
)

SPREADSHEET_ID = "1WEGXNH47jHydGSC4QfWa7XXdFCIs5xt4UO1XVonLjHI"
WORKSHEET_NAME = "Input"

REQUIRED_COLUMNS = [
    "日付",
    "区分",
    "収益カテゴリ",
    "勘定科目",
    "固定変動区分",
    "自己投資フラグ",
    "金額",
    "内容",
]


def load_credentials():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes,
        )

    credentials_path = Path("credentials.json")
    if not credentials_path.exists():
        raise FileNotFoundError("credentials.json が見つかりません。")

    return Credentials.from_service_account_file(
        str(credentials_path),
        scopes=scopes,
    )


@st.cache_data(ttl=60)
def load_sheet_data():
    credentials = load_credentials()
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

    records = worksheet.get_all_records()

    if not records:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.DataFrame(records)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[REQUIRED_COLUMNS].copy()


def to_bool(value):
    return str(value).strip().lower() in ["true", "1", "yes", "y", "on", "チェック済み"]


def append_input_row(row_values):
    credentials = load_credentials()
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    worksheet.append_row(row_values, value_input_option="USER_ENTERED")


def append_input_rows(rows_values):
    credentials = load_credentials()
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    worksheet.append_rows(rows_values, value_input_option="USER_ENTERED")


def preprocess(df):
    df = df.copy()

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

    df["金額"] = (
        df["金額"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("¥", "", regex=False)
        .str.replace("円", "", regex=False)
        .str.strip()
    )
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)

    df["区分"] = df["区分"].astype(str).str.strip()
    df["自己投資フラグ_bool"] = df["自己投資フラグ"].apply(to_bool)

    return df.sort_values("日付", na_position="last")


def format_yen(value):
    return f"¥{value:,.0f}"


def calc_kpis(df):
    income = df.loc[df["区分"] == "収入", "金額"].sum()
    expense = df.loc[df["区分"] == "経費", "金額"].sum()
    self_investment = df.loc[df["自己投資フラグ_bool"], "金額"].sum()

    profit = income - expense
    recovery_rate = (income / self_investment * 100) if self_investment > 0 else 0
    unrecovered = self_investment - income

    return income, expense, profit, self_investment, recovery_rate, unrecovered


def monthly_summary(df):
    data = df.dropna(subset=["日付"]).copy()

    if data.empty:
        return pd.DataFrame(columns=["月", "収入", "経費", "利益"])

    data["月"] = data["日付"].dt.to_period("M").astype(str)

    monthly = data.pivot_table(
        index="月",
        columns="区分",
        values="金額",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    if "収入" not in monthly.columns:
        monthly["収入"] = 0
    if "経費" not in monthly.columns:
        monthly["経費"] = 0

    monthly["利益"] = monthly["収入"] - monthly["経費"]
    monthly["月"] = pd.to_datetime(monthly["月"], errors="coerce").dt.strftime("%Y-%m")

    return monthly[["月", "収入", "経費", "利益"]]


def make_comment(profit, recovery_rate, self_investment):
    if self_investment == 0:
        return "自己投資データがまだ登録されていません。自己投資フラグを確認してください。"

    if recovery_rate >= 100 and profit > 0:
        return "自己投資を回収できています。次は利益を安定させるフェーズです。"

    if recovery_rate >= 70:
        return "回収まであと少しです。売上を伸ばしながら経費を抑えると良さそうです。"

    if profit < 0:
        return "現在は利益がマイナスです。仕入れ・送料・固定費を見直すタイミングです。"

    return "まだ回収途中です。焦らず、売上と支出のバランスを見ていきましょう。"


def main():
    st.markdown(
        """
        <style>
        header {visibility: hidden;}
        .block-container {
            max-width: 1200px;
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 2rem;
        }
        h1 {
            font-size: 2rem !important;
        }
        .app-description {
            color: #4b5563;
            line-height: 1.7;
            margin-bottom: 0.2rem;
        }
        .tabs-top-space {
            height: 0.65rem;
        }
        .input-form-space {
            height: 0.8rem;
        }
        .section-space {
            height: 1.15rem;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.75rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
                padding-bottom: 2.5rem;
            }
            h1 {
                font-size: 1.6rem !important;
            }
            .app-description {
                font-size: 0.95rem;
            }
            .tabs-top-space {
                height: 0.85rem;
            }
            .input-form-space {
                height: 1rem;
            }
            .section-space {
                height: 1.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("副業回収ダッシュボード")
    st.markdown(
        """
        <div class="app-description">
        入力と集計を1つの画面で管理できます。<br>
        「入力」タブで登録し、「ダッシュボード」タブで回収状況を確認してください。
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        raw_df = load_sheet_data()
        df = preprocess(raw_df)
    except Exception as e:
        st.error(f"データ取得に失敗しました：{e}")
        return

    st.markdown('<div class="tabs-top-space"></div>', unsafe_allow_html=True)
    input_tab, dashboard_tab, history_tab = st.tabs(["入力", "ダッシュボード", "過去データ"])

    with input_tab:
        st.markdown('<div class="input-form-space"></div>', unsafe_allow_html=True)
        st.subheader("今月のデータ入力")
        if st.session_state.pop("show_register_success", False):
            st.success("登録しました")
        st.caption("今月分を表でまとめて入力できます。空行は保存時に自動で除外されます。")

        now = pd.Timestamp.now()
        this_month_df = df[
            (df["日付"].dt.year == now.year) & (df["日付"].dt.month == now.month)
        ].copy()
        this_month_df = this_month_df[REQUIRED_COLUMNS]
        this_month_df["自己投資フラグ"] = this_month_df["自己投資フラグ"].apply(to_bool)
        this_month_df["金額"] = pd.to_numeric(this_month_df["金額"], errors="coerce")

        empty_rows_df = pd.DataFrame(
            [
                {
                    "日付": pd.NaT,
                    "区分": "",
                    "収益カテゴリ": "",
                    "勘定科目": "",
                    "固定変動区分": "",
                    "自己投資フラグ": False,
                    "金額": None,
                    "内容": "",
                }
                for _ in range(3)
            ]
        )
        editable_df = pd.concat([this_month_df, empty_rows_df], ignore_index=True)

        edited_df = st.data_editor(
            editable_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "日付": st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
                "区分": st.column_config.SelectboxColumn("区分", options=["", "収入", "経費"]),
                "収益カテゴリ": st.column_config.TextColumn("収益カテゴリ"),
                "勘定科目": st.column_config.TextColumn("勘定科目"),
                "固定変動区分": st.column_config.SelectboxColumn(
                    "固定変動区分",
                    options=["", "固定", "変動"],
                ),
                "自己投資フラグ": st.column_config.CheckboxColumn("自己投資フラグ"),
                "金額": st.column_config.NumberColumn("金額", min_value=0, step=100),
                "内容": st.column_config.TextColumn("内容"),
            },
            key="input_table_editor",
        )

        if st.button("保存", type="primary", use_container_width=True):
            try:
                rows_to_append = []
                existing_rows = set()
                for row in this_month_df.to_dict("records"):
                    existing_rows.add(
                        (
                            "" if pd.isna(row["日付"]) else pd.to_datetime(row["日付"]).strftime("%Y-%m-%d"),
                            str(row["区分"]).strip(),
                            str(row["収益カテゴリ"]).strip(),
                            str(row["勘定科目"]).strip(),
                            str(row["固定変動区分"]).strip(),
                            "TRUE" if bool(row["自己投資フラグ"]) else "FALSE",
                            0 if pd.isna(row["金額"]) else int(row["金額"]),
                            str(row["内容"]).strip(),
                        )
                    )

                for row in edited_df.to_dict("records"):
                    row_date = row.get("日付")
                    row_type = str(row.get("区分", "")).strip()
                    row_category = str(row.get("収益カテゴリ", "")).strip()
                    row_account = str(row.get("勘定科目", "")).strip()
                    row_fixed_variable = str(row.get("固定変動区分", "")).strip()
                    row_self_invest = bool(row.get("自己投資フラグ", False))
                    row_amount = row.get("金額")
                    row_detail = str(row.get("内容", "")).strip()

                    is_empty_row = (
                        pd.isna(row_date)
                        and row_type == ""
                        and row_category == ""
                        and row_account == ""
                        and row_fixed_variable == ""
                        and not row_self_invest
                        and pd.isna(row_amount)
                        and row_detail == ""
                    )
                    if is_empty_row:
                        continue

                    date_value = "" if pd.isna(row_date) else pd.to_datetime(row_date).strftime("%Y-%m-%d")
                    amount_value = 0 if pd.isna(row_amount) else int(row_amount)

                    normalized_row = (
                        date_value,
                        row_type,
                        row_category,
                        row_account,
                        row_fixed_variable,
                        "TRUE" if row_self_invest else "FALSE",
                        amount_value,
                        row_detail,
                    )
                    if normalized_row in existing_rows:
                        continue

                    rows_to_append.append(list(normalized_row))

                if not rows_to_append:
                    st.warning("保存対象の新規行がありません。")
                else:
                    append_input_rows(rows_to_append)
                    st.session_state["show_register_success"] = True
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"登録に失敗しました：{e}")

        st.markdown('<div class="input-form-space"></div>', unsafe_allow_html=True)

    with dashboard_tab:
        if st.button("データを再読み込み", key="reload_dashboard"):
            st.cache_data.clear()
            st.rerun()

        if df.empty:
            st.warning("Inputシートにデータがありません。")
            return

        show_this_month_only = st.checkbox("今月のみ表示")
        df_filtered = df
        if show_this_month_only:
            now = pd.Timestamp.now()
            df_filtered = df[
                (df["日付"].dt.year == now.year) & (df["日付"].dt.month == now.month)
            ].copy()

        if df_filtered.empty:
            st.warning("表示対象のデータがありません。")
            return

        income, expense, profit, self_investment, recovery_rate, unrecovered = calc_kpis(df_filtered)

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.subheader("サマリー")
        col1, col2, col3 = st.columns(3)
        col1.metric("総収入", format_yen(income))
        col2.metric("総経費", format_yen(expense))
        col3.metric("事業利益", format_yen(profit))

        col4, col5 = st.columns(2)
        col4.metric("自己投資額", format_yen(self_investment))
        col5.metric("回収率", f"{recovery_rate:.1f}%")

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        if recovery_rate >= 100:
            st.success(f"回収率 {recovery_rate:.1f}%：回収完了")
        elif recovery_rate >= 70:
            st.warning(f"回収率 {recovery_rate:.1f}%：あと少し")
        else:
            st.error(f"回収率 {recovery_rate:.1f}%：回収途中")

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.subheader("回収状況")

        col_a, col_b = st.columns(2)
        col_a.metric("未回収額", format_yen(max(unrecovered, 0)))
        col_b.metric("ステータス", "回収済み" if unrecovered <= 0 else "回収中")

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.info(make_comment(profit, recovery_rate, self_investment))

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.subheader("月別推移")

        monthly = monthly_summary(df_filtered)

        if not monthly.empty:
            monthly["月"] = (
                pd.to_datetime(monthly["月"], errors="coerce")
                .dt.strftime("%Y-%m")
                .fillna("")
            )
            monthly = monthly[monthly["月"] != ""].copy()
            monthly_long = monthly.melt(
                id_vars="月",
                value_vars=["収入", "経費", "利益"],
                var_name="項目",
                value_name="金額",
            )
            monthly_long["月"] = monthly_long["月"].astype(str)
            month_labels = monthly["月"].tolist()

            fig = px.bar(
                monthly_long,
                x="月",
                y="金額",
                color="項目",
                barmode="group",
                text_auto=True,
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                title="月別収支",
                height=320,
                margin=dict(l=6, r=6, t=34, b=6),
                legend_title_text="",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                ),
            )
            fig.update_xaxes(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=month_labels,
                tickmode="array",
                tickvals=month_labels,
                ticktext=month_labels,
            )
            fig.update_yaxes(title="金額（円）", tickformat=",.0f", tickprefix="¥")
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.warning("月別グラフに表示できるデータがありません。")

    with history_tab:
        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.subheader("過去データ一覧（全期間）")

        if df.empty:
            st.warning("表示できるデータがありません。")
            return

        history_df = df.copy()
        history_df["月"] = history_df["日付"].dt.to_period("M").astype(str)
        month_options = ["すべて"] + sorted(
            [m for m in history_df["月"].dropna().unique().tolist() if m and m != "NaT"],
            reverse=True,
        )
        selected_month = st.selectbox("月で絞り込み", month_options)
        if selected_month != "すべて":
            history_df = history_df[history_df["月"] == selected_month].copy()

        display_history_df = history_df[REQUIRED_COLUMNS].copy()
        display_history_df["日付"] = display_history_df["日付"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_history_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
