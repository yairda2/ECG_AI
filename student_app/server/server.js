const express = require('express');
const bodyParser = require('body-parser');
const bcrypt = require('bcrypt');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const XLSX = require('xlsx');
const {json} = require("body-parser");
const app = express();

// Configure session middleware
app.use(session({
    secret: 'your_secret_key', // change this to a secret phrase
    resave: false,
    saveUninitialized: true,
    cookie: {secure: false, httpOnly: true} // set secure to true if using https
}));

app.use(express.json()); // for parsing application/json
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));

app.use(express.static(path.join(__dirname, '../public')));

// Function to save user data to XLSX
function saveToXLSX(userData) {
    const filePath = path.join(__dirname, 'users.xlsx');
    let workbook;
    let worksheet;

    if (fs.existsSync(filePath)) {
        // Read the existing workbook
        workbook = XLSX.readFile(filePath);
        worksheet = workbook.Sheets['users'];
        if (!worksheet) {
            // Create a new worksheet with headers if it does not exist
            worksheet = XLSX.utils.json_to_sheet([], {header: ['name', 'email', 'password']});
            workbook.Sheets['users'] = worksheet;
        }
    } else {
        // Create a new workbook and worksheet with headers
        workbook = XLSX.utils.book_new();
        worksheet = XLSX.utils.json_to_sheet([], {header: ['name', 'email', 'password']});
        XLSX.utils.book_append_sheet(workbook, worksheet, 'users');
    }

    // Append new user data
    XLSX.utils.sheet_add_json(worksheet, [userData], {
        skipHeader: true,
        origin: -1 // Append to the end of the sheet
    });

    // Write the workbook to file
    XLSX.writeFile(workbook, filePath);
}


// Registration Endpoint
app.post('/register', async (req, res) => {
    const {name, email, password} = req.body;

    const filePath = path.join(__dirname, 'users.xlsx');
    let userExists = false;

    // Check if the XLSX file exists and read it
    if (fs.existsSync(filePath)) {
        const workbook = XLSX.readFile(filePath);
        const worksheet = workbook.Sheets['users'];
        if (worksheet) {
            const users = XLSX.utils.sheet_to_json(worksheet);
            userExists = users.some(u => u.email === email);
        }
    }

    // If user already exists, send an appropriate response
    if (userExists) {
        return res.status(400).json({msg:'User already exists with this email'});
    }

    // If user does not exist, proceed with registration
    const hashedPassword = await bcrypt.hash(password, 10);
    saveToXLSX({name, email, password: hashedPassword});
    res.status(200).json({redirect: '/welcome'});
});


// Login Endpoint
app.post('/login', async (req, res) => {
    console.log("Login request received:", req.body); // Debug print for incoming request
    //message from formdata is received here and is stored in req.body as an object chenged to json
    const {email, password} = req.body;
    const filePath = path.join(__dirname, 'users.xlsx');

    // Check if the XLSX file exists
    if (!fs.existsSync(filePath)) {
        console.error('XLSX file not found:', filePath); // Debug print
        return res.status(400).send('No users registered');
    }

    // Read the workbook
    const workbook = XLSX.readFile(filePath);
    console.log('Workbook Sheet Names:', workbook.SheetNames); // Debug print

    // Specify the sheet name
    const sheetName = 'users';
    const worksheet = workbook.Sheets[sheetName];

    if (!worksheet) {
        console.error(`No worksheet named '${sheetName}' found.`);
        return res.status(500).send('Server error');
    }

    // Convert sheet to JSON
    const users = XLSX.utils.sheet_to_json(worksheet);
    console.log('Converted Users:', users);

    // Find user by email
    const user = users.find(u => u.email === email);
    if (!user) {
        console.error('User not found:', email); // Debug print
        return res.status(400).send('User not found');
    }

    // Compare password
    const match = await bcrypt.compare(password, user.password);
    if (match) {
        req.session.userId = email; // Set user email in session
        res.json({redirect: '/welcome'});

    } else {
        console.log('Incorrect password for:', email); // Debug print
        res.send('Incorrect password');
    }

});

app.get('/welcome', (req, res) => {
    if (req.session.userId) {
        res.sendFile(path.join(__dirname, '../public/views/welcome.html'));
    } else {
        res.status(401).send('Unauthorized');
    }
});

app.post('/personal-information', (req, res) => {
    if (req.session.userId) {
        res.json({redirect: '/personal-information'});
    } else {
        res.status(401).send('Unauthorized');
    }
});
// Protected Page Endpoint
app.get('/personal-information', (req, res) => {
    if (req.session.userId) {
        res.sendFile(path.join(__dirname, '../public/views/personalInformation.html'));
    } else {
        res.status(401).send('Unauthorized');
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
