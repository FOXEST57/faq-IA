import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [faqs, setFaqs] = useState([]);
  const [stats, setStats] = useState({});

  useEffect(() => {
    // Fetch FAQs
    fetch('/api/faq')
      .then(res => res.json())
      .then(data => setFaqs(data));
      
    // Fetch stats
    fetch('/api/faq/stats')
      .then(res => res.json())
      .then(data => setStats(data));
  }, []);

  // Add to existing App component
  const [improvementTips, setImprovementTips] = useState([]);
  
  useEffect(() => {
    // Fetch AI improvement tips
    fetch('/api/ai/improvement-tips')
      .then(res => res.json())
      .then(data => setImprovementTips(data));
  }, []);
  
  // Add to render:
  <div className="ai-tips">
    <h3>AI Improvement Tips</h3>
    <ul>
      {improvementTips.map((tip, i) => (
        <li key={i}>{tip}</li>
      ))}
    </ul>
  </div>
  
  return (
    <div className="App">
      <div className="stats">
        <h3>FAQ Statistics</h3>
        <p>Total: {stats.total}</p>
        <p>AI Generated: {stats.ai_generated}</p>
        <p>Manual: {stats.manual}</p>
      </div>
      
      <div className="faq-list">
        {faqs.map(faq => (
          <div key={faq.id} className="faq-item">
            <h3>{faq.question}</h3>
            <p>Source: {faq.source}</p>
            <p>Created: {new Date(faq.created_at).toLocaleDateString()}</p>
            <div className="answer">{faq.answer}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
