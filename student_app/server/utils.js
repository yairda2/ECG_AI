// Desc: Utility functions for the server
const fs = require('fs');
const XLSX = require('xlsx');

const utilsObj = {};

// Function to save user data to XLSX
utilsObj.saveToXLSX = function(userData) {
    let workbook;
    if (fs.existsSync('server/users.xlsx')) {
      const file = fs.readFileSync('server/users.xlsx');
      workbook = XLSX.read(file, { type: 'buffer' });
    } else {
      workbook = XLSX.utils.book_new();
    }
  
    let worksheet = XLSX.utils.json_to_sheet([userData], { skipHeader: true });
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Users');
    XLSX.writeFile(workbook, 'server/users.xlsx');
};

module.exports = utilsObj;
