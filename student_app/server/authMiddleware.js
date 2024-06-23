const jwt = require('jsonwebtoken');
const SECRET_KEY = 'your_secret_jwt_key';

function verifyToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) {
        if (req.accepts('html')) {
            return res.redirect(`/login?error=NoToken`);
        }
        return res.status(401).json({ message: 'No token provided' });
    }

    jwt.verify(token, SECRET_KEY, (err, decoded) => {
        if (err) {
            if (req.accepts('html')) {
                return res.redirect(`/login?error=InvalidToken`);
            }
            return res.status(401).json({ message: 'Invalid token' });
        }
        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;