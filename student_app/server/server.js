// Description: Server-side code for the ECG student app.
// Author: Yair Davidof 06/13/24 & Elyasaf sinuani
// --------------------------------------------------------

const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const cookieParser = require('cookie-parser');
const {v4: uuidv4} = require('uuid');
const path = require('path');
const fs = require('fs');
const app = express();
const cors = require('cors');
const verifyToken = require('./authMiddleware'); // Import middleware


// Middleware to parse JSON and handle cookies
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

app.use(cookieParser());
app.use(express.urlencoded({extended: true}));  // For parsing application/x-www-form-urlencoded
app.use(cors());

// Apply token verification to protected routes
app.use('/training', verifyToken);
app.use('/pre-training', verifyToken);
app.use('/chooseModelAdmin', verifyToken);
app.use('/classifiedImagesAdmin', verifyToken);
app.use('/random-image-classification', verifyToken);
app.use('/random-image', verifyToken);
app.use('/classifiedImages', verifyToken);
app.use('/classify-image', verifyToken);
app.use('/chooseModel', verifyToken);


// Middleware to check token validity and refresh if needed
function checkToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) return res.status(401).json({message: 'NoToken'});

    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        const currentTime = Math.floor(Date.now() / 1000);
        const expirationTime = decoded.exp;
        const timeLeft = expirationTime - currentTime;

        if (timeLeft < 5 * 60) {
            const newToken = jwt.sign({id: decoded.id, role: decoded.role}, SECRET_KEY, {expiresIn: '1h'});
            res.cookie('token', newToken, {httpOnly: true, secure: true});
        }

        req.user = decoded;
        next();
    } catch (err) {
        return res.status(401).json({message: 'InvalidToken'});
    }
}

app.post('/refresh-token', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).json({message: 'NoToken'});

    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        const newToken = jwt.sign({id: decoded.id, role: decoded.role}, SECRET_KEY, {expiresIn: '1h'});
        res.cookie('token', newToken, {httpOnly: true, secure: true});
        res.status(200).json({message: 'Token refreshed'});
    } catch (err) {
        res.status(401).json({message: 'InvalidToken'});
    }
});


// Secret key for JWT (should be stored securely in a real-world scenario)
const SECRET_KEY = 'your_secret_jwt_key';

// Database setup
// DB explanation:
// users table
// id: TEXT PRIMARY KEY uses for the user id
// age: INTEGER user age
// gender: TEXT use
const db = new sqlite3.Database('./database.db', sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to the SQLite database.');
        createTables();
    }
});

// Create database tables
function createTables() {
    db.serialize(() => {
        db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            avgDegree INTEGER,
            academicInstitution TEXT,
            totalEntries INTEGER,
            totalAnswers INTEGER,
            totalExams INTEGER,
            avgExamTime INTEGER,
            totalTrainTime INTEGER,
            avgAnswers INTEGER

        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS authentication (
            userId TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            token TEXT,
            expiredTime DATE,
            role TEXT DEFAULT 'user',
            termsAgreement BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS answers (
            answerId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            photoName TEXT,
            classificationSrc TEXT,
            classificationDes TEXT,
            answerSubmitTime INTEGER,
            answerChange TEXT,
            alertActivated INTEGER,
            binaryQuestion boolean,
            helpActivated boolean,
            helpTimeActivated INTEGER,
            FOREIGN KEY (userId) REFERENCES users(id)
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS exam (
            examId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            title TEXT,
            score INTEGER,
            totalExamTime INTEGER,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS imageClassification (
            imageId INTEGER PRIMARY KEY AUTOINCREMENT,
            photoName TEXT,
            classification TEXT
            )`);
    });
}


// Terms of use endpoint
app.get('/terms', (req, res) => {
    const terms = fs.readFileSync(path.join(__dirname, 'Terms.txt'), 'utf8');
    res.send(terms);
});


app.post('/register', async (req, res) => {
    const {email, password, age, gender, avgDegree, academicInstitution, termsAgreement} = req.body;
    if (!email || !password || !age || !gender || !avgDegree || !academicInstitution || termsAgreement === false) {
        return res.status(400).send('All fields are required');
    }

    // Check if the user already exists
    db.get('SELECT email FROM authentication WHERE email = ?', [email], async (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            return res.status(500).send('Server error');
        }

        if (row) {
            // User already exists, redirect to login
            return res.status(409).json({message: 'User already exists. Please log in.'}); // Status 409 Conflict
        }

        // User does not exist, proceed with registration
        const hashedPassword = await bcrypt.hash(password, 10);
        const userId = uuidv4();

        db.run('INSERT INTO users (id, age, gender, avgDegree, academicInstitution) VALUES (?, ?, ?, ?, ?)', [userId, age, gender, avgDegree, academicInstitution], (err) => {
            if (err) {
                return res.status(500).send('Error registering new user in Users table: ' + err.message);
            }
            db.run('INSERT INTO authentication (userId, email, password, termsAgreement, role) VALUES (?, ?, ?, ?, "user")', [userId, email, hashedPassword, termsAgreement], (authErr) => {
                if (authErr) {
                    return res.status(500).send('Error registering new user in Authentication table: ' + authErr.message);
                }
                res.status(200).send('User registered successfully');
            });
        });
    });
});


// Login endpoint
app.post('/login', (req, res) => {
    const {email, password} = req.body;
    const sql = `SELECT userId, password, role FROM authentication WHERE email = ?`;

    db.get(sql, [email], async (err, user) => {
        if (err) {
            console.error('Database error:', err.message);
            return res.status(500).send('Error on server side: ' + err.message);
        }
        if (!user) {
            return res.status(404).send('User not found');
        }
        if (await bcrypt.compare(password, user.password)) {
            const token = jwt.sign({id: user.userId, role: user.role}, SECRET_KEY, {expiresIn: '1h'});
            res.cookie('token', token, {httpOnly: true, secure: true});
            res.cookie('userId', user.userId, {httpOnly: true, secure: true}); // Add this line
            res.send({message: 'Login successful', redirect: 'chooseModel', role: user.role});
            //add to totalEntries in users +1
            db.run('UPDATE users SET totalEntries = totalEntries + 1 WHERE id = ?', [user.userId], (err) => {
                if (err) {
                    console.error('Error updating totalEntries:', err.message);
                }
            });
        } else {
            res.status(401).json({message: 'Invalid email or password'});
        }
    });
});


// Static pages routing
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'index.html')));
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'login.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'register.html')));
app.get('/chooseModel', verifyToken, (req, res) => {
    if (req.cookies.token) {
        const decoded = jwt.verify(req.cookies.token, SECRET_KEY);
        if (decoded.role === 'admin') {
            return res.redirect('/chooseModelAdmin');
        }
    }
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModel.html'))
});
app.get('/chooseModelAdmin', verifyToken, (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    const decoded = jwt.verify(token, SECRET_KEY);
    if (decoded.role !== 'admin') {
        return res.status(403).send('You do not have permission to access this page');
    } else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModelAdmin.html'));
    }
});

// Serve classified images for admin view
app.get('/classifiedImages', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    const decoded = jwt.verify(token, SECRET_KEY);
    if (decoded.role !== 'admin') {
        return res.status(403).send('You do not have permission to access this page');
    } else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'classifiedImagesAdmin.html'));
    }
});

// Serve the pre-train page
app.get('/pre-training', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    // all users can access the pre-train page
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'preTraining.html'));
});


// Serve the pre-test page
app.post('/pre-training', checkToken, (req, res) => {
    res.json({redirect: '/training', message: 'Redirecting to training page'});

});

// Serve the training page
app.get('/training', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'training.html'));
});

// Serve the training post page
app.post('/training',verifyToken, (req, res) => {

    const {
        photoName,
        classificationSrc,
        classificationDes,
        answerSubmitTime, // Should match `answerTime` from the form
        answerChange,
        alertActivated,
        submissionType
    } = req.body;

    const userId = req.cookies.userId;
    const date = new Date().toISOString();

    db.run('INSERT INTO answers (userId, date, photoName, classificationSrc, classificationDes, answerSubmitTime, answerChange, alertActivated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [userId, date, photoName, classificationSrc, classificationDes, answerSubmitTime, answerChange, alertActivated], (err) => {
            if (err) {
                console.error('Error inserting answer:', err.message);
                return res.status(500).send('Failed to save answer');
            }

            // Update user metrics
            db.get('SELECT totalTrainTime, totalAnswers, avgAnswers FROM users WHERE id = ?', [userId], (err, row) => {
                if (err) {
                    console.error('Error retrieving user data:', err.message);
                    return res.status(500).send('Failed to retrieve user data');
                }

                if (row) {
                    const totalTrainTime = (row.totalTrainTime || 0) + answerSubmitTime;
                    const totalAnswers = (row.totalAnswers || 0) + 1;
                    const avgAnswers =
                        // Calculate the new average, is all the answers connect to this user where the answer src like the answer des
                        (row.avgAnswers || 0) + (classificationSrc === classificationDes ? 1 : 0);

                    db.run('UPDATE users SET totalTrainTime = ?, totalAnswers = ?, avgAnswers = ? WHERE id = ?',
                        [totalTrainTime, totalAnswers, avgAnswers, userId], (err) => {
                            if (err) {
                                console.error('Error updating user data:', err.message);
                                return res.status(500).send('Failed to update user data');
                            }
                            res.status(200).send('Answer saved and user metrics updated successfully');
                        });
                } else {
                    res.status(404).send('User not found');
                }
            });
        });
});

// Handling form submission from chooseModel or chooseModelAdmin
app.post('/chooseModel',verifyToken, (req, res) => {
    const action = req.body.action;
    // Redirect or handle each action accordingly
    switch (action) {
        case 'classifiedImages':
            res.status(200).json({redirect: '/classifiedImages', message: 'Redirecting to classified images'});
            break;
        case 'Single Training':
            res.status(200).json({redirect: '/pre-training', message: 'Redirecting to pre-training page'});
            break;
        case 'Test':
            res.status(200).json({redirect: '/pre-training', message: 'Redirecting to pre-training page'});
            break;
        default:
            res.status(404).json({message: 'Action not found'});
    }
});

// Serve the classifiedImagesAdmin.html
app.get('/classifiedImagesAdmin',verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'classifiedImagesAdmin.html'));
});

// API to handle image classification from classifiedImagesAdmin.html
app.post('/classify-image',verifyToken,  (req, res) => {
    const {fileName, category} = req.body;
    // Implement image classification and file handling logic
    console.log(`Classifying image ${fileName} as ${category}`);

    // Move the image to the appropriate folder based on the category, if needed,create the folder
    const sourcePath = path.join(__dirname, '..', 'public', 'img', 'bankPhotos', fileName);
    const destPath = path.join(__dirname, '..', 'public', 'img', "graded", category, fileName);
    // Create the folder if it doesn't exist
    const folderPath = path.join(__dirname, '..', 'public', 'img', "graded", category);
    if (!fs.existsSync(folderPath)) {
        fs.mkdirSync(folderPath, {recursive: true});
    }

    fs.rename(sourcePath, destPath, (err) => {
        if (err) {
            console.error('Error moving file:', err.message);
            return res.status(500).send('Failed to classify image');
        }
    });

    // Save the classification in the database
    db.run('INSERT INTO imageClassification (photoName, classification) VALUES (?, ?)', [fileName, category], (err) => {
        if (err) {
            console.error('Error inserting classification:', err.message);
            return res.status(500).send('Failed to classify image');
        }
    });

    res.send(`Image ${fileName} classified as ${category}`);
});

// Endpoint to handle image classification for admins only, classification only.
app.get('/random-image-classification', (req, res) => {
    const imagesDir = path.join(__dirname, '..', 'public', 'img', 'bankPhotos');
    fs.readdir(imagesDir, (err, files) => {
        if (err) {
            return res.status(500).send('Failed to load images');
        }
        if (files.length === 0) {
            return res.status(404).send('No images found');
        }
        const randomIndex = Math.floor(Math.random() * files.length);
        const imagePath = files[randomIndex];
        res.json({imagePath: `../img/bankPhotos/${imagePath}`});
    });
});

// Endpoint to handle training page, choose a random image for training
app.get('/random-image',verifyToken, (req, res) => {
    const foldersDir = path.join(__dirname, '..', 'public', 'img', 'graded');

    // Read all folder names
    fs.readdir(foldersDir, {withFileTypes: true}, (err, dirents) => {
        if (err) {
            console.error('Error reading folders:', err);
            return res.status(500).send('Failed to load image folders');
        }

        const validFolders = [];
        for (const dirent of dirents) {
            if (dirent.isDirectory()) {
                validFolders.push(dirent.name);
            }
        }

        if (validFolders.length === 0) {
            return res.status(404).send('No image folders found');
        }

        let randomImagePath = '';
        let foundImage = false;

        const checkFolders = (index) => {
            if (index >= validFolders.length) {
                if (!foundImage) {
                    return res.status(404).send('No images found in any folder');
                }
                return;
            }

            const randomFolder = validFolders[Math.floor(Math.random() * validFolders.length)];
            const imagesDir = path.join(foldersDir, randomFolder);

            fs.readdir(imagesDir, (err, files) => {
                if (err) {
                    console.error('Error reading files:', err);
                    return res.status(500).send('Failed to load images');
                }

                if (files.length > 0) {
                    const randomIndex = Math.floor(Math.random() * files.length);
                    randomImagePath = path.join('..', 'img', 'graded', randomFolder, files[randomIndex]);
                    foundImage = true;
                    return res.json({imagePath: randomImagePath});
                }

                checkFolders(index + 1);
            });
        };

        checkFolders(0);
    });
});

// Endpoint to handle INFO page, data from the database on the user performance


const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));


