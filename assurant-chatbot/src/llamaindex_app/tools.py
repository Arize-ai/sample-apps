import logging
import random
from datetime import datetime
from llama_index.core.tools import FunctionTool
from typing import List

logger = logging.getLogger(__name__)

MOCK_PROFILES = [
    {
        "business_id": "TECH001",
        "industry": "Technology",
        "years_in_operation": 5,
        "annual_revenue": 2500000,
        "location": "San Francisco",
    },
    {
        "business_id": "FOOD002",
        "industry": "Restaurant",
        "years_in_operation": 12,
        "annual_revenue": 800000,
        "location": "Chicago",
    },
    {
        "business_id": "MANU003",
        "industry": "Manufacturing",
        "years_in_operation": 25,
        "annual_revenue": 15000000,
        "location": "Detroit",
    },
]


class RiskScoringTools:
    @classmethod
    def calculate_risk_score(cls) -> str:
        try:
            profile = random.choice(MOCK_PROFILES)
            risk_score = round(random.uniform(0, 1), 3)
            risk_factors = [
                "Industry volatility",
                "Years in operation",
                "Revenue stability",
                "Geographic location",
                "Market conditions",
            ]

            result = (
                f"Risk Assessment Report for {profile['industry']} Business\n"
                f"Business ID: {profile['business_id']}\n"
                f"Location: {profile['location']}\n"
                f"Years Operating: {profile['years_in_operation']}\n"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Risk Score: {risk_score}\n"
                f"Risk Category: {cls._get_risk_category(risk_score)}\n\n"
                "Key Risk Factors Analyzed:\n"
                + "\n".join(f"- {factor}" for factor in risk_factors)
            )
            return result

        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            raise

    @staticmethod
    def _get_risk_category(score: float) -> str:
        if score >= 0.8:
            return "Very High Risk"
        elif score >= 0.6:
            return "High Risk"
        elif score >= 0.4:
            return "Moderate Risk"
        elif score >= 0.2:
            return "Low Risk"
        else:
            return "Very Low Risk"

    @classmethod
    def get_all_tools(cls) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(
                fn=cls.calculate_risk_score,
                name="calculate_risk_score",
                description="Calculate risk score for a random business profile",
            )
        ]
