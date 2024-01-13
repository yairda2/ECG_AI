import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import pandas as pd
import shutil
from datetime import datetime


class ImageValidator:
    """
    The main class for the Image Validator application
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Image Validator")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.image_path = ""
        self.valid = tk.IntVar()
        self.explanations = []
        self.reason_description_map = {}

        self.create_widgets()

    def create_widgets(self):
        """
        Creates the widgets for the GUI
        :return:
        """
        select_image_btn = tk.Button(self.root, text="Select Image File", command=self.select_image)
        select_image_btn.grid(row=0, column=0, columnspan=3, pady=10)

        select_dir_btn = tk.Button(self.root, text="Select Directory", command=self.select_directory)
        select_dir_btn.grid(row=1, column=0, columnspan=3, pady=10)

        valid_label = tk.Label(self.root, text="Is the person valid?")
        valid_label.grid(row=2, column=0, columnspan=3)

        valid_yes = tk.Radiobutton(self.root, text="Valid", variable=self.valid, value=1)
        valid_yes.grid(row=3, column=0, padx=5)
        valid_no = tk.Radiobutton(self.root, text="Not Valid", variable=self.valid, value=0)
        valid_no.grid(row=3, column=1, padx=5)

        explanation_label = tk.Label(self.root, text="Reason & Description (if not valid):")
        explanation_label.grid(row=4, column=0, columnspan=3)

        line_number_label = tk.Label(self.root, text="Line Number")
        line_number_label.grid(row=5, column=0)
        reason_label = tk.Label(self.root, text="Reason")
        reason_label.grid(row=5, column=1)
        description_label = tk.Label(self.root, text="Description")
        description_label.grid(row=5, column=2)

        self.line_number_entries = []
        self.reason_entries = []
        self.description_entries = []
        for i in range(15):
            line_number_entry = tk.Entry(self.root, width=5)
            line_number_entry.insert(tk.END, str(i + 1))
            reason_entry = tk.Entry(self.root)
            description_entry = tk.Entry(self.root)
            line_number_entry.grid(row=i + 6, column=0, padx=5)
            reason_entry.grid(row=i + 6, column=1, padx=5)
            description_entry.grid(row=i + 6, column=2, padx=5)
            self.line_number_entries.append(line_number_entry)
            self.reason_entries.append(reason_entry)
            self.description_entries.append(description_entry)

        save_btn = tk.Button(self.root, text="Save", command=self.save_data)
        save_btn.grid(row=21, column=0, columnspan=3, pady=10)

    def select_image(self):
        """
        Selects the image to be validated
        :return:
        """
        self.image_path = filedialog.askopenfilename()
        if self.image_path:
            if os.path.isdir(self.image_path):
                # next to the button dir, show the selected dir path, not only massage box
                messagebox.showinfo("Directory Selected", f"You are working on directory: {self.image_path}")
                # add the code to show the selected dir name
                self.clear_entries_except_line_numbers()


            else:
                # next to the button, show the selected image
                messagebox.showinfo("Image Selected", f"You are working on image: {self.image_path}")
                # if self.image_path.endswith((".jpg", ".jpeg", ".png")):
                image = Image.open(self.image_path)
                image.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(image)
                img_label = tk.Label(self.root, image=photo)
                img_label.image = photo
                img_label.grid(row=0, column=3, rowspan=18, padx=10)

    def select_directory(self):
        """
        Selects the directory containing the images
        :return:
        """
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.image_path = dir_path
            messagebox.showinfo("Directory Selected", f"You are working on directory: {self.image_path}")
            self.clear_image()  # Clear the displayed image

    def save_data(self):
        """
        Saves the data to Excel and copies the image to the 'photos' folder
        :return:
        """
        if not self.image_path:
            messagebox.showerror("Error", "Please select an image or directory.")
            return

        # Get the value of the valid/invalid radio button
        valid_value = self.valid.get()

        if os.path.isdir(self.image_path):
            # Directory processing logic (added in the previous code segment)
            processed_images = []
            for filename in os.listdir(self.image_path):
                if filename.endswith((".jpg", ".jpeg", ".png")):
                    image_name = os.path.basename(filename)
                    if self.image_not_in_excel(image_name):
                        destination = os.path.join("photos", image_name)
                        os.makedirs("photos", exist_ok=True)
                        shutil.copy(os.path.join(self.image_path, filename), destination)

                        reason = self.reason_entries[0].get()
                        description = self.description_entries[0].get()

                        if (reason, description) not in self.reason_description_map:
                            self.reason_description_map[(reason, description)] = [image_name]
                        else:
                            self.reason_description_map[(reason, description)].append(image_name)

                        # Saving details to Excel
                        data = {
                            "Image Path": [image_name],
                            "Validation": ["Valid" if valid_value == 1 else "Invalid"],  # Include the 'Valid'/'Invalid' value,
                            "Reason": [reason],
                            "Description": [description]
                        }
                        df = pd.DataFrame(data)

                        excel_filename = "validation_data.xlsx"

                        if os.path.exists(excel_filename):
                            existing_data = pd.read_excel(excel_filename)
                            existing_data = pd.concat([existing_data, df], ignore_index=True)
                            existing_data.to_excel(excel_filename, index=False)
                        else:
                            df.to_excel(excel_filename, index=False)

                        processed_images.append(image_name)
                    else:
                        messagebox.showinfo("Info", f"Image '{image_name}' already exists in the data.")

            if processed_images:
                processed_str = ", ".join(processed_images)
                messagebox.showinfo("Success", f"Images {processed_str} processed and copied to 'photos' folder.")
        else:
            # Existing logic for single image processing remains unchanged
            image_name = os.path.basename(self.image_path)
            if not self.image_not_in_excel(image_name):
                messagebox.showinfo("Info", f"Image '{image_name}' already exists in the data.")
                return # Exit the function
            destination = os.path.join("photos", image_name)
            os.makedirs("photos", exist_ok=True)
            Image.open(self.image_path).save(destination)

            reason = self.reason_entries[0].get()
            description = self.description_entries[0].get()

            if (reason, description) not in self.reason_description_map:
                self.reason_description_map[(reason, description)] = [image_name]
            else:
                self.reason_description_map[(reason, description)].append(image_name)

            # Saving details to Excel
            data = {
                "Image Path": [image_name],
                "Validation": ["Valid" if valid_value == 1 else "Invalid"],  # Include the 'Valid'/'Invalid' value,
                "Reason": [reason],
                "Description": [description]
            }
            df = pd.DataFrame(data)

            excel_filename = "validation_data.xlsx"

            if os.path.exists(excel_filename):
                existing_data = pd.read_excel(excel_filename)
                existing_data = pd.concat([existing_data, df], ignore_index=True)
                existing_data.to_excel(excel_filename, index=False)
            else:
                df.to_excel(excel_filename, index=False)

            messagebox.showinfo("Success", "Data saved and image copied to 'photos' folder.")

        self.clear_entries_except_line_numbers()

    def image_not_in_excel(self, image_name):
        """
        Checks if the image is already present in the Excel file
        :param image_name:
        :return:
        """
        excel_filename = "validation_data.xlsx"
        if os.path.exists(excel_filename):
            existing_data = pd.read_excel(excel_filename)
            return image_name not in existing_data["Image Path"].values
        return True

    def on_close(self):
        """
        Handles the closing of the application
        :return:
        """
        excel_filename = "validation_data.xlsx"
        if os.path.exists(excel_filename):
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = os.path.join(backup_dir, f"backup_validation_data_{timestamp}.xlsx")
            shutil.copy(excel_filename, backup_filename)

        self.root.destroy()

    def clear_entries_except_line_numbers(self):
        """
        Clears the reason and description entries
        :return:
        """
        for entry in self.reason_entries:
            entry.delete(0, tk.END)
        for entry in self.description_entries:
            entry.delete(0, tk.END)
        # Clear the displayed image
        self.clear_image()
        self.image_path = ""

    def clear_image(self):
        """
        Clears the image displayed on the GUI
        :return:
        """
        img_labels = self.root.grid_slaves(row=0, column=3)
        if img_labels:
            img_label = img_labels[0]
            img_label.grid_forget()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageValidator(root)
    root.mainloop()
