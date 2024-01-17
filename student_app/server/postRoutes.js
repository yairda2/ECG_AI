// Purpose: Handle POST requests to the server
const express = require('express');
const bcrypt = require('bcrypt');
const utilsModule = require('./utils');
const fs = require('fs');
const XLSX = require('xlsx');

const router = express.Router();

router.post('/', (req, res) => {
    // Handle POST request
    res.send('Response for POST');

});
// Registration Endpoint
router.post('/register', async (req, res) => {
  // Handle POST request for registration
    console.log(req.body);
    console.log("req.body.email");
    res.send('Response for POST register elyasaf light');
  // ...
});

// Login Endpoint
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    if (!fs.existsSync('server/users.xlsx')) {
        return res.status(404).send('No users registered');
    }

    const workbook = XLSX.readFile('server/users.xlsx');
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];
    const users = XLSX.utils.sheet_to_json(worksheet);

    const user = users.find(u => u.email === email);
    if (!user) {
        return res.status(404).send('User not found');
    }

    const match = await bcrypt.compare(password, user.password);
    if (match) {
        res.send('Login successful');
    } else {
        res.send('Incorrect password');
    }
});


module.exports = router;
