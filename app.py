"""Web UI - Ticket Triage System"""
import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

from flask import Flask, render_template_string, request, jsonify
from ticket_triage import process_ticket, process_tickets_batch, SAMPLE_TICKETS

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>מערכת ניתוב פניות חכמה</title>
    <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:'Segoe UI',Tahoma,sans-serif;background:#f8fafc;color:#1e293b;min-height:100vh}
        .header{background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:25px;text-align:center}
        .header h1{font-size:1.8em;color:#fff;margin-bottom:6px}
        .header p{color:#94a3b8;font-size:.85em}
        .container{max-width:1100px;margin:20px auto;padding:0 20px}
        .hint{text-align:center;font-size:.78em;color:#94a3b8;margin-bottom:10px;font-style:italic}
        .input-section{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
        .input-section h2{color:#4f46e5;margin-bottom:12px;font-size:1.1em}
        textarea{width:100%;height:80px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;color:#1e293b;padding:12px;font-size:.95em;resize:vertical;direction:rtl}
        textarea:focus{outline:none;border-color:#4f46e5;box-shadow:0 0 0 3px rgba(79,70,229,.1)}
        .btn-row{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
        .btn{padding:10px 20px;border:none;border-radius:8px;font-size:.9em;cursor:pointer;font-weight:600;transition:all .2s}
        .btn-primary{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff}
        .btn-primary:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(79,70,229,.3)}
        .btn-secondary{background:#f1f5f9;color:#475569;border:1px solid #e2e8f0}
        .btn-secondary:hover{background:#e2e8f0;color:#1e293b}
        .btn-danger{background:#fee2e2;color:#dc2626;font-size:.8em;padding:8px 14px}
        .btn-danger:hover{background:#fecaca}
        .filters{background:#fff;border-radius:12px;padding:15px;margin-bottom:15px;border:1px solid #e2e8f0;display:flex;gap:10px;flex-wrap:wrap;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,.05)}
        .filters label{font-size:.8em;color:#64748b}
        .filters select{background:#f8fafc;border:1px solid #e2e8f0;color:#1e293b;padding:6px 10px;border-radius:6px;font-size:.85em}
        .table-wrap{background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
        table{width:100%;border-collapse:collapse}
        thead th{background:#f8fafc;padding:12px 15px;font-size:.75em;color:#4f46e5;text-align:right;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid #e2e8f0}
        tbody tr{border-top:1px solid #f1f5f9;transition:background .2s;cursor:pointer}
        tbody tr:hover{background:#f8fafc}
        tbody td{padding:14px 15px;font-size:.9em;line-height:1.5;white-space:normal;word-wrap:break-word}
        .badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.75em;font-weight:700}
        .badge-critical{background:#dc2626;color:#fff}
        .badge-high{background:#ea580c;color:#fff}
        .badge-medium{background:#2563eb;color:#fff}
        .badge-low{background:#16a34a;color:#fff}
        .badge-human{background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;box-shadow:0 2px 4px rgba(245,158,11,.3)}
        .badge-auto{background:linear-gradient(135deg,#06b6d4,#0891b2);color:#fff;box-shadow:0 2px 4px rgba(6,182,212,.3)}
        .expanded-row{display:none;background:#f8fafc;border-top:1px solid #e2e8f0}
        .expanded-row.active{display:table-row}
        .expanded-row td{padding:15px 20px;color:#475569;font-size:.85em;line-height:1.8;white-space:normal;word-wrap:break-word}
        .loading{display:none;text-align:center;padding:20px}
        .loading.active{display:block}
        .spinner{width:30px;height:30px;border:3px solid #e2e8f0;border-top-color:#4f46e5;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 10px}
        @keyframes spin{to{transform:rotate(360deg)}}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:15px}
        .stat-box{background:#fff;border-radius:10px;padding:15px;text-align:center;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
        .stat-box .num{font-size:1.8em;font-weight:700;color:#4f46e5}
        .stat-box .desc{font-size:.75em;color:#64748b;margin-top:3px}
        .empty-state{text-align:center;padding:40px;color:#475569;font-size:.95em}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎫 מערכת ניתוב פניות חכמה</h1>
        <p>Ticket Triage System - ניתוב וסיווג פניות לקוחות</p>
    </div>
    <div class="container">
        <div class="input-section">
            <h2>📝 פנייה נכנסת</h2>
            <textarea id="ticketInput" style="height:100px" placeholder="הכניסי פנייה כאן (ממייל / וואטסאפ / טופס / כל מקור)..."></textarea>
            <div class="btn-row">
                <button class="btn btn-primary" onclick="processOne()">עבד פנייה</button>
                <button class="btn btn-secondary" onclick="loadAndProcess()">📋 12 פניות לדוגמה</button>
                <button class="btn btn-danger" onclick="clearAll()"> נקה</button>
            </div>
        </div>
        <div id="statsArea"></div>
        <div class="filters">
            <label>סינון:</label>
            <select id="filterCategory" onchange="applyFilters()">
                <option value="all">כל הקטגוריות</option>
                <option value="תמיכה_טכנית">תמיכה טכנית</option>
                <option value="חיוב_ותשלומים">חיוב ותשלומים</option>
                <option value="מכירות">מכירות</option>
                <option value="שירות_לקוחות">שירות לקוחות</option>
                <option value="אבטחה">אבטחה</option>
                <option value="כללי">כללי</option>
            </select>
            <select id="filterUrgency" onchange="applyFilters()">
                <option value="all">כל הדחיפויות</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
            </select>
            <select id="filterHuman" onchange="applyFilters()">
                <option value="all">הכל</option>
                <option value="true">טיפול אנושי</option>
                <option value="false">אוטומטי</option>
            </select>
        </div>
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>מעבד עם AI...</p>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>סיכום <span style="font-weight:400;font-size:.9em;color:#94a3b8">(לחצי לפרטים)</span></th>
                        <th>קטגוריה</th>
                        <th>דחיפות</th>
                        <th>טיפול</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
            <div class="empty-state" id="emptyState">אין פניות עדיין. שלחי פנייה או לחצי על "12 פניות לדוגמה"</div>
        </div>
    </div>
    <script>
        let allResults = [];
        let counter = 0;

        function addResult(r) {
            counter++;
            r._id = counter;
            allResults.push(r);
            renderTable();
        }

        function renderTable() {
            const catFilter = document.getElementById('filterCategory').value;
            const urgFilter = document.getElementById('filterUrgency').value;
            const humFilter = document.getElementById('filterHuman').value;

            let filtered = allResults.filter(r => {
                if (catFilter !== 'all' && r.category !== catFilter) return false;
                if (urgFilter !== 'all' && r.urgency !== urgFilter) return false;
                if (humFilter !== 'all' && String(r.human_required) !== humFilter) return false;
                return true;
            });

            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = filtered.map(r => `
                <tr onclick="toggleExpand(${r._id})" data-id="${r._id}">
                    <td>${r._id}</td>
                    <td>${r.summary}</td>
                    <td>${r.category.replace('_',' ')}</td>
                    <td><span class="badge badge-${r.urgency}">${r.urgency}</span></td>
                    <td><span class="badge ${r.human_required?'badge-human':'badge-auto'}">${r.human_required?'אנושי':'אוטומטי'}</span></td>
                </tr>
                <tr class="expanded-row" id="expand-${r._id}">
                    <td colspan="5"><strong>פנייה מקורית:</strong><br>${r.text}</td>
                </tr>
            `).join('');

            document.getElementById('emptyState').style.display = filtered.length ? 'none' : 'block';
            updateStats();
        }

        function toggleExpand(id) {
            const row = document.getElementById('expand-' + id);
            row.classList.toggle('active');
        }

        function updateStats() {
            if (allResults.length === 0) { document.getElementById('statsArea').innerHTML=''; return; }
            const human = allResults.filter(r=>r.human_required).length;
            const critical = allResults.filter(r=>r.urgency==='critical').length;
            document.getElementById('statsArea').innerHTML = `<div class="stats">
                <div class="stat-box"><div class="num">${allResults.length}</div><div class="desc">סה״כ פניות</div></div>
                <div class="stat-box"><div class="num">${human}</div><div class="desc">טיפול אנושי</div></div>
                <div class="stat-box"><div class="num">${allResults.length-human}</div><div class="desc">אוטומטי</div></div>
                <div class="stat-box"><div class="num" style="color:#fca5a5">${critical}</div><div class="desc">קריטי</div></div>
            </div>`;
        }

        function applyFilters() { renderTable(); }

        function loadAndProcess() {
            fetch('/get_samples').then(r=>r.json()).then(data => {
                document.getElementById('loading').classList.add('active');
                let done = 0;
                const total = data.samples.length;
                for (let i = 0; i < total; i++) {
                    fetch('/process', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tickets:[data.samples[i]]})})
                    .then(res => res.json())
                    .then(d => {
                        if (d.results[0]) addResult(d.results[0]);
                        done++;
                        if (done >= total) document.getElementById('loading').classList.remove('active');
                    });
                }
            });
        }

        async function processOne() {
            const text = document.getElementById('ticketInput').value.trim();
            if (!text) return alert('הכניסי פנייה!');
            document.getElementById('loading').classList.add('active');
            const res = await fetch('/process', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tickets:[text]})});
            const data = await res.json();
            document.getElementById('loading').classList.remove('active');
            addResult(data.results[0]);
            document.getElementById('ticketInput').value = '';
        }

        function clearAll() {
            allResults = [];
            counter = 0;
            renderTable();
        }
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/get_samples')
def get_samples():
    return jsonify(samples=SAMPLE_TICKETS)

@app.route('/process', methods=['POST'])
def process():
    tickets = request.json.get('tickets', [])
    results = [process_ticket(t) for t in tickets]
    return jsonify(results=results)

@app.route('/process_samples', methods=['POST'])
def process_samples():
    results = process_tickets_batch(SAMPLE_TICKETS)
    return jsonify(results=results)

@app.route('/process_one_sample', methods=['POST'])
def process_one_sample():
    idx = request.json.get('idx', 0)
    if idx < len(SAMPLE_TICKETS):
        result = process_ticket(SAMPLE_TICKETS[idx])
        return jsonify(result=result, idx=idx)
    return jsonify(result=None, idx=idx)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  http://localhost:8080")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=8080)
