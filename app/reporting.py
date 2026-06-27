# app/reporting.py
import os
import io
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Template

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ReportGenerator:
    """Generate PDF reports for clients"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        os.makedirs(self.template_dir, exist_ok=True)
    
    def generate_report(self, campaign_data: Dict, metrics: Dict, analysis: Dict) -> bytes:
        if not REPORTLAB_AVAILABLE:
            return self._generate_text_report(campaign_data, metrics, analysis)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title', parent=styles['Heading1'], fontSize=24,
            textColor=colors.HexColor('#0f1117'), spaceAfter=30
        )
        heading_style = ParagraphStyle(
            'Heading', parent=styles['Heading2'], fontSize=16,
            textColor=colors.HexColor('#238636'), spaceAfter=12
        )
        
        story = []
        title = Paragraph(f"Marketing Performance Report", title_style)
        story.append(title)
        story.append(Spacer(1, 0.25*inch))
        
        campaign_name = campaign_data.get('client_name', 'Unknown Campaign')
        story.append(Paragraph(f"Campaign: {campaign_name}", styles['Normal']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Executive Summary", heading_style))
        summary = analysis.get('summary', 'Campaign performing within expected ranges.')
        story.append(Paragraph(summary, styles['Normal']))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Key Performance Indicators", heading_style))
        
        metrics_data = [
            ['Metric', 'Value'],
            ['Impressions', f"{metrics.get('impressions', 0):,}"],
            ['Clicks', f"{metrics.get('clicks', 0):,}"],
            ['CTR', f"{metrics.get('ctr', 0)}%"],
            ['CPC', f"${metrics.get('cpc', 0):.2f}"],
            ['Conversions', f"{metrics.get('conversions', 0)}"],
            ['ROAS', f"{metrics.get('roas', 0)}x"],
            ['Total Spend', f"${metrics.get('cost', 0):.2f}"],
        ]
        
        table = Table(metrics_data, colWidths=[2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Optimization Recommendations", heading_style))
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                action = rec.get('action', '')
                priority = rec.get('priority', 'medium')
                impact = rec.get('expected_impact', '')
                story.append(Paragraph(f"• {action} ({priority} priority) - {impact}", styles['Normal']))
        else:
            story.append(Paragraph("No specific recommendations at this time.", styles['Normal']))
        
        if analysis.get('creative_feedback'):
            story.append(Paragraph("Creative Feedback", heading_style))
            story.append(Paragraph(analysis['creative_feedback'], styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _generate_text_report(self, campaign_data: Dict, metrics: Dict, analysis: Dict) -> bytes:
        report = f"""
        ========================================
        MARKETING PERFORMANCE REPORT
        ========================================
        
        Campaign: {campaign_data.get('client_name', 'Unknown')}
        Date: {datetime.now().strftime('%B %d, %Y')}
        
        ========================================
        EXECUTIVE SUMMARY
        ========================================
        {analysis.get('summary', 'Campaign performing within expected ranges.')}
        
        ========================================
        KEY PERFORMANCE INDICATORS
        ========================================
        Impressions:     {metrics.get('impressions', 0):,}
        Clicks:          {metrics.get('clicks', 0):,}
        CTR:             {metrics.get('ctr', 0)}%
        CPC:             ${metrics.get('cpc', 0):.2f}
        Conversions:     {metrics.get('conversions', 0)}
        ROAS:            {metrics.get('roas', 0)}x
        Total Spend:     ${metrics.get('cost', 0):.2f}
        
        ========================================
        RECOMMENDATIONS
        ========================================
        """
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                action = rec.get('action', '')
                priority = rec.get('priority', 'medium')
                impact = rec.get('expected_impact', '')
                report += f"- [{priority}] {action} - {impact}\n"
        else:
            report += "No specific recommendations at this time.\n"
        return report.encode('utf-8')