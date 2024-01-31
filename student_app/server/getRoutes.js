// Desc: GET routes for the server
const express = require('express');
const router = express.Router();

// Default GET route
router.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});


router.get('/add', (req, res) => {
  // Handle GET request
  res.send('Response for GET');
});

// Add more GET routes here

module.exports = router;
