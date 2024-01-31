// Desc: This file contains the configuration for the express app.
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const getRoutes = require('./getRoutes');
const postRoutes = require('./postRoutes');

const app = express();
app.use(bodyParser.json());

// Serve static files from the 'public' directory
app.use(express.static(path.join(__dirname, '../public')));

// Use the routers
app.use(getRoutes);
app.use(postRoutes);

module.exports = app;
