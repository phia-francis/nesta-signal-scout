const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const OpenAI = require('openai');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// --- CONFIGURATION ---
const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(bodyParser.json());

// Load Secrets
const OPENAI_API_KEY = process.env.OPENAI_API_KEY; 
const ASSISTANT_ID = process.env.ASSISTANT_ID || 'asst_6AnFZkW7f6Jhns774D9GNWXr'; 

if (!OPENAI_API_KEY) {
  console.error("CRITICAL ERROR: OPENAI_API_KEY is missing.");
  process.exit(1);
}

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

// --- DATABASE SETUP (SQLite) ---
const DB_PATH = path.join(__dirname, 'nesta_signals.db');
const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) console.error("DB Error:", err.message);
  else console.log("✅ Connected to SQLite database.");
});

// Create Table
db.run(`CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    hook TEXT,
    score INTEGER,
    mission TEXT,
    archetype TEXT,
    url TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)`);

// --- HELPER: WIDGET JSON BUILDER ---
function buildWidgetPayload(data) {
  const score = data.score || 0;
  const scoreColor = score > 80 ? "success" : (score > 60 ? "warning" : "secondary");
  const archetype = (data.archetype || "SIGNAL").toUpperCase();
  const lenses = data.lenses || "Tech, Social";

  // Note: We escape double quotes for the JSON string used in the onclick handler
  const safeJson = JSON.stringify(data).replace(/"/g, "&quot;");

  return {
    "type": "Card",
    "size": "lg",
    "children": [
      {
        "type": "Col", "gap": 2,
        "children": [
          { "type": "Row", "align": "center", "children": [
              { "type": "Icon", "name": "sparkle", "color": "primary" },
              { "type": "Title", "value": "Nesta Signal Scout", "size": "sm" }
          ]},
          { "type": "Text", "value": "Signal identified.", "size": "sm", "color": "secondary" }
        ]
      },
      { "type": "Divider" },
      {
        "type": "Col", "gap": 2,
        "children": [
          { "type": "Row", "align": "center", "children": [
              { "type": "Caption", "value": archetype, "size": "sm", "color": "tertiary" },
              { "type": "Spacer" },
              { "type": "Badge", "label": `Score: ${score}`, "color": scoreColor }
          ]},
          { "type": "Title", "value": data.title, "size": "md" },
          { "type": "Text", "value": data.hook, "size": "md" },
          {
            "type": "Row", "gap": 2, "align": "center",
            "children": [
              { "type": "Badge", "label": data.mission, "color": "info" },
              { "type": "Spacer" },
              // SAVE BUTTON LOGIC
              { 
                "type": "Button", 
                "label": "Save", 
                "iconStart": "bookmark", 
                "size": "sm",
                // We send the raw data back to the client to handle the save
                "onClickAction": { "type": "custom.save", "payload": data } 
              },
              { 
                "type": "Button", "label": "Source", "variant": "outline", "size": "sm", "iconStart": "external-link",
                "onClickAction": { "type": "open.url", "payload": { "url": data.sourceURL } } 
              }
            ]
          }
        ]
      }
    ]
  };
}

// --- ROUTE 1: CHAT ---
app.post('/api/chat', async (req, res) => {
  try {
    let userMessage = "Find top signals";
    if (req.body.messages) userMessage = req.body.messages[req.body.messages.length - 1].content;
    else if (req.body.text) userMessage = req.body.text;

    console.log(`User asked: "${userMessage}"`);

    const run = await openai.beta.threads.createAndRun({
      assistant_id: ASSISTANT_ID,
      thread: { messages: [{ role: "user", content: userMessage }] }
    });

    let runStatus = await openai.beta.threads.runs.retrieve(run.thread_id, run.id);

    while (runStatus.status !== 'completed') {
      if (runStatus.status === 'failed') throw new Error("Agent Failed");
      
      if (runStatus.status === 'requires_action') {
        const toolCalls = runStatus.required_action.submit_tool_outputs.tool_calls;
        const displayAction = toolCalls.find(tc => tc.function.name === 'display_signal_card');

        if (displayAction) {
          const signalData = JSON.parse(displayAction.function.arguments);
          // Return the Widget Card immediately
          return res.json(buildWidgetPayload(signalData));
        }
      }
      
      await new Promise(r => setTimeout(r, 1000));
      runStatus = await openai.beta.threads.runs.retrieve(run.thread_id, run.id);
    }

    const messages = await openai.beta.threads.messages.list(run.thread_id);
    return res.json({ role: "assistant", content: messages.data[0].content[0].text.value });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// --- ROUTE 2: SAVE SIGNAL ---
app.post('/api/save', (req, res) => {
  const data = req.body;
  const sql = `INSERT INTO signals (title, hook, score, mission, archetype, url) VALUES (?, ?, ?, ?, ?, ?)`;
  const params = [data.title, data.hook, data.score, data.mission, data.archetype, data.sourceURL];

  db.run(sql, params, function(err) {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ message: "Saved", id: this.lastID });
  });
});

// --- ROUTE 3: VIEW DATABASE ---
app.get('/api/view_db', (req, res) => {
  db.all("SELECT * FROM signals ORDER BY id DESC", [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
