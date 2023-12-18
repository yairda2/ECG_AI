import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import pandas as pd
import shutil
from datetime import datetime
current_dir = os.path.dirname(os.path.abspath(__file__))
class ImageValidator:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Validator")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.image_path = ""
        self.valid = tk.IntVar()
        self.explanations = []

        self.create_widgets()

    def create_widgets(self):
        select_image_btn = tk.Button(self.root, text="Select Image", command=self.select_image)
        select_image_btn.grid(row=0, column=0, columnspan=3, pady=10)

        valid_label = tk.Label(self.root, text="Is the person valid?")
        valid_label.grid(row=1, column=0, columnspan=3)

        valid_yes = tk.Radiobutton(self.root, text="Valid", variable=self.valid, value=1)
        valid_yes.grid(row=2, column=0, padx=5)
        valid_no = tk.Radiobutton(self.root, text="Not Valid", variable=self.valid, value=0)
        valid_no.grid(row=2, column=1, padx=5)

        explanation_label = tk.Label(self.root, text="Reason & Description (if not valid):")
        explanation_label.grid(row=3, column=0, columnspan=3)

        line_number_label = tk.Label(self.root, text="Line Number")
        line_number_label.grid(row=4, column=0)
        reason_label = tk.Label(self.root, text="Reason")
        reason_label.grid(row=4, column=1)
        description_label = tk.Label(self.root, text="Description")
        description_label.grid(row=4, column=2)

        self.line_number_entries = []
        self.reason_entries = []
        self.description_entries = []
        for i in range(15):
            line_number_entry = tk.Entry(self.root, width=5)
            line_number_entry.insert(tk.END, str(i + 1))
            reason_entry = tk.Entry(self.root)
            description_entry = tk.Entry(self.root)
            line_number_entry.grid(row=i + 5, column=0, padx=5)
            reason_entry.grid(row=i + 5, column=1, padx=5)
            description_entry.grid(row=i + 5, column=2, padx=5)
            self.line_number_entries.append(line_number_entry)
            self.reason_entries.append(reason_entry)
            self.description_entries.append(description_entry)

        save_btn = tk.Button(self.root, text="Save", command=self.save_data)
        save_btn.grid(row=20, column=0, columnspan=3, pady=10)

    def select_image(self):
        self.image_path = filedialog.askopenfilename()
        if self.image_path:
            self.clear_entries_except_line_numbers()
            image = Image.open(self.image_path)
            image.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(image)
            img_label = tk.Label(self.root, image=photo)
            img_label.image = photo
            img_label.grid(row=0, column=3, rowspan=18, padx=10)

    def save_data(self):
        if not self.image_path:
            messagebox.showerror("Error", "Please select an image.")
            return

        image_name = os.path.basename(self.image_path)
        destination = os.path.join(f'{current_dir}/photos', image_name)
        os.makedirs("photos", exist_ok=True)
        Image.open(self.image_path).save(destination)

        data = {
            "Image Path": [image_name],
            "Validity": ["Valid" if self.valid.get() == 1 else "Not Valid"]
        }

        for i in range(15):
            data[f"Reason {i + 1}"] = self.reason_entries[i].get()
            data[f"Description {i + 1}"] = self.description_entries[i].get()

        df = pd.DataFrame(data)

        excel_filename = "validation_data.xlsx"

        if os.path.exists(f'{current_dir}/{excel_filename}'):
            existing_data = pd.read_excel(excel_filename)

            existing_image_names = existing_data["Image Path"].tolist()
            if image_name in existing_image_names:
                messagebox.showinfo("Information", f"Image '{image_name}' already exists in the data.")
                return

            existing_data = pd.concat([existing_data, df], ignore_index=True)
            existing_data.to_excel(f'{current_dir}/{excel_filename}', index=False)
        else:
            df.to_excel(f'{current_dir}/{excel_filename}', index=False)
            # Copy the image to the 'photos' directory
        shutil.copy(self.image_path, destination)
        messagebox.showinfo("Success", f"Data saved to {excel_filename} and image copied to 'photos' folder.")

    def on_close(self):
        excel_filename = "validation_data.xlsx"
        if os.path.exists(excel_filename):
            backup_dir = f'{current_dir}/"backups'
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = os.path.join(backup_dir, f"backup_validation_data_{timestamp}.xlsx")
            shutil.copy(excel_filename, backup_filename)

        self.root.destroy()

    def clear_entries_except_line_numbers(self):
        for entry in self.reason_entries:
            entry.delete(0, tk.END)
        for entry in self.description_entries:
            entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageValidator(root)
    root.mainloop()
