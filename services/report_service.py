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
            
        # 获取今日交易数据
        today = datetime.now().date()
        data = self.firefly_service.get_transactions_summary(
            user_config.firefly_api_url,
            user_config.firefly_access_token,
            start_date=today,
            end_date=today
        )
        
        if data:
            # 调用Dify生成报告
            prompt = "请生成今日财务报告"
            return self._call_dify_api(user_config, prompt, data, 'daily')
        
        return None
    
    def generate_weekly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成周报"""
        if not user_config.report_config or not user_config.report_config.weekly_enabled:
            return None
            
        # 获取本周交易数据
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        data = self.firefly_service.get_transactions_summary(
            user_config.firefly_api_url,
            user_config.firefly_access_token,
            start_date=start_of_week,
            end_date=today
        )
        
        if data:
            # 调用Dify生成报告
            prompt = "请生成本周财务报告"
            return self._call_dify_api(user_config, prompt, data, 'weekly')
        
        return None
    
    def generate_monthly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成月报"""
        if not user_config.report_config or not user_config.report_config.monthly_enabled:
            return None
            
        # 获取本月交易数据
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        data = self.firefly_service.get_transactions_summary(
            user_config.firefly_api_url,
            user_config.firefly_access_token,
            start_date=start_of_month,
            end_date=today
        )
        
        if data:
            # 调用Dify生成报告
            prompt = "请生成本月财务报告"
            return self._call_dify_api(user_config, prompt, data, 'monthly')
        
        return None
    
    def generate_yearly_report(self, user_config: UserConfig) -> Optional[str]:
        """生成年报"""
        if not user_config.report_config or not user_config.report_config.yearly_enabled:
            return None
            
        # 获取本年交易数据
        today = datetime.now().date()
        start_of_year = today.replace(month=1, day=1)
        data = self.firefly_service.get_transactions_summary(
            user_config.firefly_api_url,
            user_config.firefly_access_token,
            start_date=start_of_year,
            end_date=today
        )
        
        if data:
            # 调用Dify生成报告
            prompt = "请生成本年度财务报告"
            return self._call_dify_api(user_config, prompt, data, 'yearly')
        
        return None
    
    def _call_dify_api(self, user_config: UserConfig, prompt: str, context_data: Dict[str, Any], report_type: str) -> Optional[str]:
        """调用 Dify API 生成报告"""
        try:
            if not user_config.dify_config or not user_config.dify_config.enabled:
                logger.warning(f"用户 {user_config.user_id} 未配置或未启用 Dify")
                return self._generate_fallback_report(context_data, report_type)

            # 使用 DifyService
            dify_service = DifyService(user_config.dify_config.api_key)

            # 生成报告
            result = dify_service.generate_financial_report(
                workflow_id=user_config.dify_config.workflow_id,
                report_type=report_type,
                transaction_data=context_data,
                report_query=prompt
            )

            if result['success']:
                message = result['message']
                # 检查返回的内容是否是有效的财务报告
                if self._is_valid_financial_report(message):
                    logger.info(f"成功生成用户 {user_config.user_id} 的 {report_type} 报告")
                    return message
                else:
                    logger.warning(f"Dify返回的内容不是有效的财务报告，使用后备报告")
                    return self._generate_fallback_report(context_data, report_type)
            else:
                logger.error(f"生成报告失败: {result.get('error')}，使用后备报告")
                return self._generate_fallback_report(context_data, report_type)
                
        except Exception as e:
            logger.error(f"生成报告时发生错误: {e}，使用后备报告")
            return self._generate_fallback_report(context_data, report_type)
    
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