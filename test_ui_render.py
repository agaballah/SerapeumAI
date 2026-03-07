import customtkinter as ctk
import tkinter as tk

ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("400x400")
app.configure(fg_color="#121212")

frame = ctk.CTkFrame(app, fg_color="#1A1A1A", width=300, height=300)
frame.pack(pady=20, padx=20, fill="both", expand=True)

# Test 1: Standard ctk Label with transparent
l1 = ctk.CTkLabel(frame, text="Test 1: CTK Transparent", fg_color="transparent", text_color="white")
l1.pack(pady=10)

# Test 2: Standard ctk Label with explicit hex
l2 = ctk.CTkLabel(frame, text="Test 2: CTK Hex", fg_color="#1A1A1A", text_color="white")
l2.pack(pady=10)

# Test 3: Standard tk Label with explicit hex
l3 = tk.Label(frame, text="Test 3: TK Hex", bg="#1A1A1A", fg="white")
l3.pack(pady=10)

# Test 4: CTK Button (Buttons seem to work in the user screenshot)
b1 = ctk.CTkButton(frame, text="Test 4: CTK Button", fg_color="#1A1A1A", hover_color="#2D2D2D", text_color="white")
b1.pack(pady=10)

app.mainloop()
