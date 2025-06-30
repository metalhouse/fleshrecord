import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models.user_config import UserConfig
from services.firefly_service import FireflyService
from services.dify_service import DifyService

logger = logging.getLogger(__name__)


class ReportService:
    """财务报告服务"""
    
    def __init__(self, dify_api_url: str, firefly_service: FireflyService):
        self.dify_api_url = dify_api_url.rstrip('/')
        self.firefly_service = firefly_service
    
    def generate_daily_report(self, user_config: UserConfig) -> Optional[str]:
        """生成日报"""
        if not user_config.report_config or not user_config.report_config.daily_enabled:
            return None
        prompt = user_config.report_config.daily_prompt
        return self._call_dify_api(user_config, prompt, report_type='daily')
    
    def generate_weekly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成周报"""
        if not user_config.report_config or not user_config.report_config.weekly_enabled:
            return None
        prompt = user_config.report_config.weekly_prompt
        return self._call_dify_api(user_config, prompt, report_type='weekly')
    
    def generate_monthly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成月报"""
        if not user_config.report_config or not user_config.report_config.monthly_enabled:
            return None
        prompt = user_config.report_config.monthly_prompt
        return self._call_dify_api(user_config, prompt, report_type='monthly')
    
    def generate_yearly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成年报"""
        if not user_config.report_config or not user_config.report_config.yearly_enabled:
            return None
        prompt = user_config.report_config.yearly_prompt
        return self._call_dify_api(user_config, prompt, report_type='yearly')
    
    def _call_dify_api(self, user_config: UserConfig, prompt: str, report_type: str) -> Optional[str]:
        """调用 Dify API 生成报告，只发送 prompt，不附加交易数据"""
        try:
            if not user_config.dify_config or not user_config.dify_config.enabled:
                logger.warning(f"用户 {user_config.user_id} 未配置或未启用 Dify")
                return None
            dify_service = DifyService(user_config.dify_config.api_key)
            result = dify_service.generate_financial_report(
                workflow_id=user_config.dify_config.workflow_id,
                report_type=report_type,
                transaction_data=None,
                report_query=prompt
            )
            return result
        except Exception as e:
            logger.error(f"调用 Dify API 生成报告失败: {e}")
            return None
    
    def _is_valid_financial_report(self, content: str) -> bool:
        """检查内容是否是有效的财务报告"""
        if not content or len(content.strip()) < 20:
            return False
        
        # 检查是否包含API相关的JSON格式内容（不是财务报告）
        if 'api_endpoint' in content or 'query_parameters' in content:
            return False
            
        # 检查是否包含财务相关的关键词
        financial_keywords = ['收入', '支出', '余额', '交易', '财务', '报告', '分析', '总计']
        return any(keyword in content for keyword in financial_keywords)
    
    def _generate_fallback_report(self, context_data: Dict[str, Any], report_type: str) -> str:
        """生成后备财务报告"""
        try:
            period = context_data.get('period', '未知时期')
            transaction_count = context_data.get('transaction_count', 0)
            total_income = context_data.get('total_income', 0)
            total_expense = context_data.get('total_expense', 0)
            net_amount = context_data.get('net_amount', 0)
            
            report_titles = {
                'daily': '📊 每日财务报告',
                'weekly': '📈 每周财务报告',
                'monthly': '📋 每月财务报告',
                'yearly': '📊 年度财务报告'
            }
            
            title = report_titles.get(report_type, '财务报告')
            
            report = f"""{title}
━━━━━━━━━━━━━━━━━━━━
📅 统计期间：{period}

💰 财务概况：
• 总收入：¥{total_income:,.2f}
• 总支出：¥{total_expense:,.2f}
• 净收入：¥{net_amount:,.2f}
• 交易笔数：{transaction_count}

📊 财务分析：
"""
            
            if transaction_count == 0:
                report += "• 本期无交易记录\n• 建议关注日常消费记录"
            elif net_amount > 0:
                report += f"• 本期实现净收入 ¥{net_amount:,.2f}\n• 财务状况良好，继续保持"
            elif net_amount < 0:
                report += f"• 本期净支出 ¥{abs(net_amount):,.2f}\n• 建议控制支出，关注预算管理"
            else:
                report += "• 本期收支平衡\n• 财务状况稳定"
            
            if context_data.get('error'):
                report += f"\n\n⚠️ 注意：数据获取时遇到问题：{context_data['error']}"
                
            report += "\n\n💡 温馨提示：定期记录和分析财务数据有助于更好地管理个人财务。"
            
            return report
            
        except Exception as e:
            logger.error(f"生成后备报告失败: {e}")
            return f"📊 {report_type.title()}财务报告\n\n抱歉，报告生成遇到问题，请稍后重试。"