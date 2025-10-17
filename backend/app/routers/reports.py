from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from datetime import datetime
from pydantic import BaseModel

from ..database import get_db
from .. import models, schemas

class PDFReportRequest(BaseModel):
    session_id: int
    role: str
    level: str
    total_recording_time: int
    transcript: List[dict]
    sentiment_analysis: List[dict]
    bias_alerts: List[dict]
    questions_asked: List[dict]
    question_performance: dict = None
    session_summary: str = ""
    generated_at: str


router = APIRouter()


def _generate_local_summary(text: str) -> str:
    # Simple local heuristic summarizer: first N sentences + heuristics
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    top = '. '.join(sentences[:5])
    if not top:
        top = text[:500]
    return (top + ('.' if not top.endswith('.') else ''))[:1500]


@router.post("/", response_model=schemas.ReportOut)
def create_report(payload: schemas.ReportCreate, db: Session = Depends(get_db)):
    s = db.query(models.InterviewSession).get(payload.session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    items = db.query(models.TranscriptItem).filter(models.TranscriptItem.session_id == payload.session_id).order_by(models.TranscriptItem.timestamp_ms.asc()).all()
    full_text = '\n'.join(i.text for i in items)
    summary = _generate_local_summary(full_text)
    r = models.Report(session_id=payload.session_id, summary_text=summary)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("/{report_id}", response_model=schemas.ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Report).get(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


@router.get("/{report_id}/pdf")
def report_pdf(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Report).get(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, f"Session Report #{r.id}")
    y -= 24
    c.setFont("Helvetica", 10)
    text_obj = c.beginText(72, y)
    for line in r.summary_text.split('\n'):
        for chunk in [line[i:i+90] for i in range(0, len(line), 90)]:
            text_obj.textLine(chunk)
    c.drawText(text_obj)
    c.showPage()
    c.save()
    buffer.seek(0)
    return io.BytesIO(buffer.read())


@router.post("/generate-pdf")
def generate_comprehensive_pdf(request: PDFReportRequest):
    """Generate a comprehensive PDF report with all interview data"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=TA_CENTER)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=12)
        normal_style = styles['Normal']
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("AI Interview Assistant - Comprehensive Report", title_style))
        story.append(Spacer(1, 12))
        
        # Session Information
        story.append(Paragraph("Session Information", heading_style))
        session_info = f"""
        <b>Session ID:</b> {request.session_id}<br/>
        <b>Role:</b> {request.role}<br/>
        <b>Level:</b> {request.level}<br/>
        <b>Recording Duration:</b> {request.total_recording_time} seconds<br/>
        <b>Generated:</b> {request.generated_at}<br/>
        """
        story.append(Paragraph(session_info, normal_style))
        story.append(Spacer(1, 20))
        
        # Questions Asked & Performance
        if request.questions_asked:
            story.append(Paragraph("Questions Asked & Performance", heading_style))
            
            # Question Performance Summary
            if request.question_performance:
                perf = request.question_performance
                perf_text = f"""
                <b>Overall Performance:</b> {perf.get('performanceLevel', 'N/A')}<br/>
                <b>Average Rating:</b> {perf.get('averageRating', 'N/A')}/5<br/>
                <b>Questions Rated:</b> {perf.get('totalRated', 0)}/{perf.get('totalQuestions', 0)}<br/>
                <b>Rating Distribution:</b><br/>
                &nbsp;&nbsp;• Excellent (5): {perf.get('ratingDistribution', {}).get('5', 0)}<br/>
                &nbsp;&nbsp;• Good (4): {perf.get('ratingDistribution', {}).get('4', 0)}<br/>
                &nbsp;&nbsp;• Average (3): {perf.get('ratingDistribution', {}).get('3', 0)}<br/>
                &nbsp;&nbsp;• Below Average (2): {perf.get('ratingDistribution', {}).get('2', 0)}<br/>
                &nbsp;&nbsp;• Poor (1): {perf.get('ratingDistribution', {}).get('1', 0)}<br/>
                """
                story.append(Paragraph(perf_text, normal_style))
                story.append(Spacer(1, 12))
            
            # Individual Questions
            for i, q in enumerate(request.questions_asked[:15], 1):
                question_text = q.get('question', q.get('question_text', 'N/A'))
                difficulty = q.get('difficulty', 'Unknown')
                rating = q.get('rating')
                notes = q.get('notes', '')
                
                question_info = f"<b>{i}. [{difficulty.upper()}]</b> {question_text}"
                if rating:
                    rating_desc = {1: 'Poor', 2: 'Below Average', 3: 'Average', 4: 'Good', 5: 'Excellent'}.get(rating, 'Unknown')
                    question_info += f"<br/>&nbsp;&nbsp;<b>Rating:</b> {rating}/5 ({rating_desc})"
                if notes:
                    question_info += f"<br/>&nbsp;&nbsp;<b>Notes:</b> {notes}"
                
                story.append(Paragraph(question_info, normal_style))
                story.append(Spacer(1, 8))
            story.append(Spacer(1, 20))
        
        # Sentiment Analysis Summary
        if request.sentiment_analysis:
            story.append(Paragraph("Sentiment Analysis Summary", heading_style))
            positive_count = sum(1 for s in request.sentiment_analysis if s.get('sentiment') == 'positive')
            negative_count = sum(1 for s in request.sentiment_analysis if s.get('sentiment') == 'negative')
            neutral_count = len(request.sentiment_analysis) - positive_count - negative_count
            
            sentiment_summary = f"""
            <b>Total Analysis Points:</b> {len(request.sentiment_analysis)}<br/>
            <b>Positive:</b> {positive_count} ({positive_count/len(request.sentiment_analysis)*100:.1f}%)<br/>
            <b>Negative:</b> {negative_count} ({negative_count/len(request.sentiment_analysis)*100:.1f}%)<br/>
            <b>Neutral:</b> {neutral_count} ({neutral_count/len(request.sentiment_analysis)*100:.1f}%)<br/>
            """
            story.append(Paragraph(sentiment_summary, normal_style))
            story.append(Spacer(1, 20))
        
        # Bias Alerts
        if request.bias_alerts:
            story.append(Paragraph("Bias Detection Alerts", heading_style))
            story.append(Paragraph(f"<b>Total Bias Alerts:</b> {len(request.bias_alerts)}", normal_style))
            for alert in request.bias_alerts:
                story.append(Paragraph(f"• {alert.get('alert', 'N/A')}", normal_style))
            story.append(Spacer(1, 20))
        
        # Complete Transcript Section
        if request.transcript:
            story.append(Paragraph("Complete Interview Transcript", heading_style))
            story.append(Paragraph(f"<b>Total Transcript Entries:</b> {len(request.transcript)}", normal_style))
            story.append(Spacer(1, 12))
            
            # Full transcript text (complete conversation)
            full_transcript_text = " ".join([entry.get('text', '') for entry in request.transcript if entry.get('text', '').strip()])
            if full_transcript_text:
                story.append(Paragraph("Full Conversation:", heading_style))
                # Split long text into paragraphs for better readability
                transcript_paragraphs = full_transcript_text.split('. ')
                current_paragraph = ""
                for sentence in transcript_paragraphs:
                    if len(current_paragraph + sentence) < 500:  # Keep paragraphs reasonable length
                        current_paragraph += sentence + ". "
                    else:
                        if current_paragraph:
                            story.append(Paragraph(current_paragraph.strip(), normal_style))
                            story.append(Spacer(1, 6))
                        current_paragraph = sentence + ". "
                
                # Add the last paragraph
                if current_paragraph:
                    story.append(Paragraph(current_paragraph.strip(), normal_style))
                
                story.append(Spacer(1, 20))
            
            # Detailed transcript table (all entries, not just first 20)
            story.append(Paragraph("Detailed Transcript Entries:", heading_style))
            transcript_data = [['Time', 'Text', 'Sentiment', 'Bias']]
            
            # Process all transcript entries
            for entry in request.transcript:
                time_str = datetime.fromtimestamp(entry.get('timestamp_ms', 0) / 1000).strftime('%H:%M:%S')
                text = entry.get('text', '')
                # Truncate very long text but keep more than before
                if len(text) > 150:
                    text = text[:150] + '...'
                sentiment = entry.get('sentiment_label', 'N/A')
                bias = 'Yes' if entry.get('bias_flagged') else 'No'
                transcript_data.append([time_str, text, sentiment, bias])
            
            # Create table with all entries
            transcript_table = Table(transcript_data, colWidths=[1*inch, 3.5*inch, 0.8*inch, 0.7*inch])
            transcript_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(transcript_table)
        
        # Comprehensive Session Summary
        if request.session_summary:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Comprehensive Session Summary", heading_style))
            # Split the summary into paragraphs for better formatting
            summary_lines = request.session_summary.split('\n')
            for line in summary_lines:
                if line.strip():
                    if line.startswith('#'):
                        # This is a heading
                        heading_level = line.count('#')
                        if heading_level == 1:
                            story.append(Paragraph(line.replace('#', '').strip(), styles['Heading1']))
                        elif heading_level == 2:
                            story.append(Paragraph(line.replace('#', '').strip(), styles['Heading2']))
                        else:
                            story.append(Paragraph(line.replace('#', '').strip(), styles['Heading3']))
                    elif line.startswith('- '):
                        # This is a bullet point
                        story.append(Paragraph(f"• {line[2:]}", normal_style))
                    else:
                        # Regular paragraph
                        story.append(Paragraph(line, normal_style))
                    story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=interview-report-{request.session_id}.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@router.get("/{session_id}/transcript.csv")
def transcript_csv(session_id: int, db: Session = Depends(get_db)):
    items = db.query(models.TranscriptItem).filter(models.TranscriptItem.session_id == session_id).order_by(models.TranscriptItem.timestamp_ms.asc()).all()
    import csv
    buffer = io.StringIO()
    w = csv.writer(buffer)
    w.writerow(["timestamp_ms", "text", "sentiment_label", "sentiment_score", "bias_flagged"])
    for i in items:
        w.writerow([i.timestamp_ms, i.text, i.sentiment_label or '', i.sentiment_score or '', 'yes' if i.bias_flagged else 'no'])
    buffer.seek(0)
    return buffer.getvalue()


