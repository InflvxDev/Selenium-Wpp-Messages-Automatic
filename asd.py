# chats = driver.find_elements(By.XPATH, "//div[@role='row']")

            # for chat in chats:
            #     chat.click()
            #     time.sleep(3)

            #     nombre_contacto = driver.find_element(By.XPATH, "//header//span").text
            #     mensajes = driver.find_elements(By.XPATH, "//div[contains(@class, 'message-in')]")

            #     print(nombre_contacto)

            #     if mensajes:  # Verifica que la lista no esté vacía
            #         ultimo_mensaje = mensajes[-1].text
            #     else:
            #      continue  

            #     if nombre_contacto not in estado_usuarios:
            #         estado_usuarios[nombre_contacto] = "inicio"
                
            #     estado_actual = estado_usuarios[nombre_contacto]

            #     if estado_actual == "inicio":
            #         if "cita" in ultimo_mensaje.lower():
            #             enviar_mensaje(nombre_contacto, "¿Quieres consultar una cita? Responde 'Si' o 'No'.")
            #             estado_usuarios[nombre_contacto] = "esperando_confirmacion"

            #     elif estado_actual == "esperando_confirmacion":
            #         if "si" in ultimo_mensaje.lower():
            #             enviar_mensaje(nombre_contacto, "Por favor, dime tu numero de documento.")
            #             estado_usuarios[nombre_contacto] = "esperando_documento"
            #         else:
            #             enviar_mensaje(nombre_contacto, "Entendido si necesitas algo, avisame")
            #             estado_usuarios[nombre_contacto] = "inicio"
                
            #     elif estado_actual == "esperando_documento":
            #         if ultimo_mensaje.isdigit():
            #             cita = buscar_cita(ultimo_mensaje)
            #             if cita:
            #                 mensaje = f"Tienes una cita con el {cita['medico']} en {cita['especialidad']} el {cita['fechaCita']}."
            #             else:
            #                 mensaje = "No encontre ninguna cita con ese documento."
                        
            #             enviar_mensaje(nombre_contacto, mensaje)
            #             estado_usuarios[nombre_contacto] = "inicio"
                    
            #         else: 
            #             enviar_mensaje(nombre_contacto, "Por favor, ingresa un número de documento válido.")