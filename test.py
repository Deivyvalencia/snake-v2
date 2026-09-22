import customtkinter as ctk

app = ctk.CTk()
app.geometry("800x500")
app.title("Prueba CustomTkinter")

label = ctk.CTkLabel(app, text="¡Funciona!")
label.pack(pady=20)

app.mainloop()
