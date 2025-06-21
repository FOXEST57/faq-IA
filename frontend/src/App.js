import React, { useState, useEffect } from 'react';
import './App.css';
import {
  Accordion, AccordionSummary, AccordionDetails,
  Typography, TextField, Button, Box, CircularProgress,
  Alert, Chip, IconButton
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SearchIcon from '@mui/icons-material/Search';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

function App() {
  const [faqData, setFaqData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showBackToTop, setShowBackToTop] = useState(false);

  // Get unique categories from FAQ data
  const categories = ['all', ...new Set(faqData.map(item => item.category || 'general'))];

  useEffect(() => {
    const fetchFaqData = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/faq');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setFaqData(data);
        setFilteredData(data);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchFaqData();

    // Back to top button visibility
    const handleScroll = () => {
      setShowBackToTop(window.pageYOffset > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // Filter logic
    let result = faqData;
    
    if (searchTerm) {
      result = result.filter(item => 
        item.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.answer.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    if (selectedCategory !== 'all') {
      result = result.filter(item => 
        (item.category || 'general') === selectedCategory
      );
    }
    
    setFilteredData(result);
  }, [searchTerm, selectedCategory, faqData]);

  const handleBackToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Error loading FAQ data: {error.message}
        </Alert>
      </Box>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>FAQ - Assisted by AI</h1>
      </header>
      
      <main style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
        <Box mb={4}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search FAQs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon color="action" />,
            }}
          />
          
          <Box mt={2} display="flex" flexWrap="wrap" gap={1}>
            {categories.map(category => (
              <Chip
                key={category}
                label={category}
                onClick={() => setSelectedCategory(category)}
                color={selectedCategory === category ? 'primary' : 'default'}
                variant={selectedCategory === category ? 'filled' : 'outlined'}
              />
            ))}
          </Box>
        </Box>

        <h2>Frequently Asked Questions</h2>
        
        {filteredData.length === 0 ? (
          <Typography variant="body1" color="textSecondary">
            No FAQs match your search criteria.
          </Typography>
        ) : (
          <div className="faq-list">
            {filteredData.map((item) => (
              <Accordion key={item.id} sx={{ mb: 1, '&:hover': { boxShadow: '0 2px 8px rgba(0,0,0,0.1)' } }}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  sx={{ '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' } }}
                >
                  <Typography variant="subtitle1" fontWeight={500}>
                    {item.question}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ backgroundColor: '#f9f9f9' }}>
                  <Typography>{item.answer}</Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </div>
        )}

        {showBackToTop && (
          <IconButton
            onClick={handleBackToTop}
            sx={{
              position: 'fixed',
              bottom: '20px',
              right: '20px',
              backgroundColor: 'primary.main',
              color: 'white',
              '&:hover': { backgroundColor: 'primary.dark' }
            }}
          >
            <KeyboardArrowUpIcon />
          </IconButton>
        )}
      </main>
    </div>
  );
}

export default App;
