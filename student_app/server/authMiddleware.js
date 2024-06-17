// authMiddleware.js
const jwt = require('jsonwebtoken');
const SECRET_KEY = 'your_secret_jwt_key'; // Ensure this matches the one used in your server

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        return res.status(401).json({ message: 'NoToken' }); // No token found
    }

    jwt.verify(token, SECRET_KEY, (err, decoded) => {
        if (err) {
            if (err.name === 'TokenExpiredError') {
                return res.status(401).json({ message: 'TokenExpired' }); // Token expired
            } else {
                return res.status(401).json({ message: 'InvalidToken' }); // Invalid token
            }
        }
        req.user = decoded; // Store decoded token in req.user for further use
        next();
    });
}

module.exports = verifyToken;
