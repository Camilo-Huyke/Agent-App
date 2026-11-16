import tkinter as tk

current_file_chat = "chat.txt"

def insertar_mensaje(text_widget, END):

    text = " "

    try:
        with open("chat.txt", "r", encoding='utf-8') as f:
            text = f.read()
        text_widget.delete('1.0', END)
        text_widget.insert(END, text)
    except Exception as e:
        print(e)

def set_mensaje(text_widget):

    try:
        with open(current_file_chat, "w", encoding='utf-8') as f:
            f.write(text_widget.get('1.0', 'end'))
    except Exception as e:
        print(e)



main = tk.Tk()
main.title("Chat Agents")

text_chat = tk.Text(main, height=20, width=100)

entry_message_wg = tk.Entry(main)

send_button = tk.Button(main, text="send", width=10,command=lambda:set_mensaje(text_chat))

text_chat.grid(row=0, column=0)
entry_message_wg.grid(row=1, column=0)
send_button.grid(row=1, column=1)


main.mainloop()