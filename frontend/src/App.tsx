import { useState, useEffect } from 'react';
import { 
  LayoutDashboard,
  LogOut,
  RefreshCw,
  Video,
  Send,
  User
} from 'lucide-react';
import './index.css';

function App() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [telegramId, setTelegramId] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/api/events')
      .then(r => r.json())
      .then(data => setEvents(data))
      .catch(e => console.error(e));
  }, []);

  const handleSync = async () => {
    setLoading(true);
    try {
      await fetch('http://localhost:8000/api/sync', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
    setTimeout(() => setLoading(false), 1000);
  };

  const handleTelegramLink = async () => {
    if (!telegramId) return;
    try {
      await fetch('http://localhost:8000/api/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: telegramId })
      });
      alert('Linked!');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="dashboard-container">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="logo">
          <div style={{width: 24, height: 24, borderRadius: '50%', backgroundColor: 'var(--primary-green)'}}></div>
          Nudge<span>Box</span>
        </div>

        <div className="user-profile">
          <div className="avatar" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-green)'}}>
            <User size={32} />
          </div>
          <div className="user-name">Chaitanya</div>
        </div>

        <ul className="nav-menu">
          <li className="nav-item active"><LayoutDashboard size={20} /> Dashboard</li>
        </ul>

        <div className="nav-item" style={{ marginTop: 'auto' }}>
          <LogOut size={20} /> Log out
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        <div className="header">
          <h1>DASHBOARD</h1>
        </div>

        <div className="dashboard-grid">
          
          {/* COLUMN 1 */}
          <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
            
            {/* Link Telegram Widget */}
            <div className="card">
              <div className="card-title">Telegram Notifications</div>
              <p style={{fontSize: 14, color: 'var(--text-muted)'}}>
                Receive immediate push notifications for your upcoming interviews and assessments.
              </p>
              <div className="telegram-input">
                <input 
                  type="text" 
                  placeholder="Paste Chat ID" 
                  value={telegramId}
                  onChange={(e) => setTelegramId(e.target.value)}
                />
                <button onClick={handleTelegramLink}><Send size={16} /></button>
              </div>
            </div>

            {/* Sync Mailbox Widget */}
            <div className="card" style={{flex: 1}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20}}>
                <div className="card-title" style={{marginBottom: 0}}>Mailbox Sync</div>
                <button className="sync-btn" onClick={handleSync}>
                  <RefreshCw size={16} className={loading ? "spin" : ""} /> Sync Now
                </button>
              </div>
              <p style={{fontSize: 14, color: 'var(--text-muted)', marginBottom: 15}}>
                NudgeBox automatically scans your Gmail for new interview invites every 10 minutes.
              </p>
              <div className="list-item">
                <div className="item-icon"><div style={{width: 10, height: 10, borderRadius: '50%', backgroundColor: 'var(--accent-bright)'}}></div></div>
                <div className="item-details">
                  <div className="item-title">Status: Connected</div>
                  <div className="item-subtitle">Last synced: Just now</div>
                </div>
              </div>
            </div>

          </div>

          {/* COLUMN 2 */}
          <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
            
            {/* Upcoming Events */}
            <div className="card" style={{flex: 1}}>
              <div className="card-title">Upcoming events</div>
              
              <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
                {events.length === 0 && <div style={{color: 'var(--text-muted)'}}>No upcoming events found.</div>}
                {events.map(event => (
                  <div key={event._id} className="pill event-item">
                    <div className="item-icon" style={{backgroundColor: 'white'}}>
                      <Video size={20} />
                    </div>
                    <div className="pill-content">
                      <div className="item-title">{event.company} - {event.role}</div>
                      <div className="item-subtitle">{event.local_time_str}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN - Dark Stats */}
          <div className="right-column">
            
            <div className="stat-card">
              <div className="stat-title">Detection Accuracy</div>
              <div style={{position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 100, height: 100}}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="8" />
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#81c995" strokeWidth="8" strokeDasharray="251.2" strokeDashoffset="0" strokeLinecap="round" transform="rotate(-90 50 50)" />
                </svg>
                <span style={{position: 'absolute', fontSize: 24, fontWeight: 700}}>100%</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-title">Active Workflows</div>
              <div style={{position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 100, height: 100}}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="8" />
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#fbbc04" strokeWidth="8" strokeDasharray="251.2" strokeDashoffset="75" strokeLinecap="round" transform="rotate(-90 50 50)" />
                </svg>
                <span style={{position: 'absolute', fontSize: 24, fontWeight: 700}}>3</span>
              </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}

export default App;
