// authMiddleware.js
const jwt = require('jsonwebtoken');
const config = require('../config/config');
const SECRET_KEY = config.secret_key.key;

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        res.redirect('/login?message=InvalidToken');
    }

    jwt.verify(token, SECRET_KEY, (err, decoded) => {
        if (err) {
            res.redirect('/login?message=InvalidToken');
        }
        // if the time over reLogin
        if (Date.now() >= decoded.exp * 1000) {
            res.redirect('/login?message=TokenExpired');
        }
        req.user = decoded;
        // TODO Add here check if the id exists in the database
        next();
    });
}

module.exports = verifyToken;
