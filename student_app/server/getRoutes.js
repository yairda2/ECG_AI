// Desc: GET routes for the server
const express = require('express');
const router = express.Router();

// Example GET route
router.get('/someGetEndpoint', (req, res) => {
  // Handle GET request
  res.send('Response for GET');
});

// Add more GET routes here

module.exports = router;
