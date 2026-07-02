# app/reporting.py
"""
PDF Report Generation with Font Fallback and Error Handling
"""
import os
import io
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def setup_font():
    """Register a system font for PDF generation with fallback strategy."""
    if not REPORTLAB_AVAILABLE:
        return None
    
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf',
        '/System/Library/Fonts/Helvetica.ttf',
        '/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                font_name = 'CustomFont'
                pdfmetrics.registerFont(TTFont(font_name, path))
                print(f"[Reporting] ✅ Font loaded: {path}")
                return font_name
            except Exception as e:
                print(f"[Reporting] ⚠️  Failed to load {path}: {e}")
                continue
    
    print("[Reporting] Using default Helvetica font")
    return 'Helvetica'


class ReportGenerator:
    """Generate PDF reports for campaigns with font fallback"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        self.font_name = setup_font()
    
    def generate_report(self, campaign_data: Dict, metrics: Dict, analysis: Dict) -> bytes:
        """Generate a PDF report with fallback to text if PDF generation fails."""
        if not REPORTLAB_AVAILABLE:
            print("[Reporting] ⚠️  ReportLab not available, generating text report")
            return self._generate_text_report(campaign_data, metrics, analysis)
        
        try:
            return self._generate_pdf_report(campaign_data, metrics, analysis)
        except Exception as e:
            print(f"[Reporting] ❌ PDF generation failed: {e}, falling back to text")
            return self._generate_text_report(campaign_data, metrics, analysis)
    
    def _generate_pdf_report(self, campaign_data: Dict, metrics: Dict, analysis: Dict) -> bytes:
        """Generate PDF report with proper font handling."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Use fallback font or Helvetica
        font_name = self.font_name or 'Helvetica'
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            fontName=font_name,
            textColor=colors.HexColor('#0f1117'),
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=16,
            fontName=font_name,
            textColor=colors.HexColor('#238636'),
            spaceAfter=12
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=11,
            textColor=colors.HexColor('#24292f')
        )
        
        story = []
        
        # Title
        title = Paragraph(f"Marketing Performance Report", title_style)
        story.append(title)
        story.append(Spacer(1, 0.25 * inch))
        
        # Campaign Info
        campaign_name = campaign_data.get('client_name', 'Unknown Campaign')
        story.append(Paragraph(f"Campaign: {campaign_name}", normal_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", normal_style))
        story.append(Spacer(1, 0.25 * inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        summary = analysis.get('summary', 'Campaign performing within expected ranges.')
        story.append(Paragraph(summary, normal_style))
        story.append(Spacer(1, 0.25 * inch))
        
        # Key Performance Indicators
        story.append(Paragraph("Key Performance Indicators", heading_style))
        
        metrics_data = [
            ['Metric', 'Value'],
            ['Impressions', f"{int(metrics.get('impressions', 0)):,}"],
            ['Clicks', f"{int(metrics.get('clicks', 0)):,}"],
            ['CTR', f"{float(metrics.get('ctr', 0)):.2f}%"],
            ['CPC', f"${float(metrics.get('cpc', 0)):.2f}"],
            ['Conversions', f"{int(metrics.get('conversions', 0))}"],
            ['ROAS', f"{float(metrics.get('roas', 0)):.2f}x"],
            ['Total Spend', f"${float(metrics.get('cost', 0)):.2f}"],
        ]
        
        table = Table(metrics_data, colWidths=[2 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), font_name),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('FONTNAME', (0, 1), (1, -1), font_name),
            ('FONTSIZE', (0, 1), (1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.25 * inch))
        
        # Optimization Recommendations
        story.append(Paragraph("Optimization Recommendations", heading_style))
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                action = rec.get('action', '')
                priority = rec.get('priority', 'medium')
                impact = rec.get('expected_impact', '')
                rec_text = f"• {action} ({priority} priority) - {impact}"
                story.append(Paragraph(rec_text, normal_style))
        else:
            story.append(Paragraph("No specific recommendations at this time.", normal_style))
        
        # Creative Feedback
        if analysis.get('creative_feedback'):
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph("Creative Feedback", heading_style))
            story.append(Paragraph(analysis['creative_feedback'], normal_style))
        
        # Build PDF
        try:
            doc.build(story)
            buffer.seek(0)
            print("[Reporting] ✅ PDF report generated successfully")
            return buffer.getvalue()
        except Exception as e:
            print(f"[Reporting] ❌ PDF build failed: {e}")
            raise
    
    def _generate_text_report(self, campaign_data: Dict, metrics: Dict, analysis: Dict) -> bytes:
        """Generate plain text report as fallback."""
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
Impressions:     {int(metrics.get('impressions', 0)):,}
Clicks:          {int(metrics.get('clicks', 0)):,}
CTR:             {float(metrics.get('ctr', 0)):.2f}%
CPC:             ${float(metrics.get('cpc', 0)):.2f}
Conversions:     {int(metrics.get('conversions', 0))}
ROAS:            {float(metrics.get('roas', 0)):.2f}x
Total Spend:     ${float(metrics.get('cost', 0)):.2f}

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
                report += f"- [{priority.upper()}] {action}\n  Impact: {impact}\n\n"
        else:
            report += "No specific recommendations at this time.\n"
        
        if analysis.get('creative_feedback'):
            report += f"\n========================================\nCREATIVE FEEDBACK\n========================================\n{analysis['creative_feedback']}\n"
        
        report += "\n========================================\nEND OF REPORT\n========================================\n"
        
        return report.encode('utf-8')
