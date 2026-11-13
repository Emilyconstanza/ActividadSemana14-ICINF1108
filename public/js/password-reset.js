// El script se carga de forma síncrona en <head>, antes de cualquier recurso
// externo. El token permanece en este cierre; no se escribe en almacenamiento.
;(() => {
	const isReset = window.location.pathname.replace(/\/$/, "") === "/reset-password"
	let token = ""
	if (isReset) {
		const url = new URL(window.location.href)
		token = url.searchParams.get("token") ?? ""
		url.searchParams.delete("token")
		window.history.replaceState(null, "", url.pathname + url.search + url.hash)
	}

	document.addEventListener("DOMContentLoaded", async () => {
		const form = document.getElementById(isReset ? "reset-password-form" : "forgot-password-form")
		const feedback = document.getElementById("feedback")
		if (!(form instanceof HTMLFormElement) || !feedback) return
		const button = form.querySelector('button[type="submit"]')
		if (!(button instanceof HTMLButtonElement)) return
		const idleLabel = button.textContent
		let busy = false

		function message(text, error = false) {
			feedback.textContent = text
			feedback.hidden = false
			feedback.setAttribute("role", error ? "alert" : "status")
			feedback.classList.toggle("text-red-700", error)
			feedback.classList.toggle("text-emerald-800", !error)
		}

		function fieldError(name, text) {
			const input = form.elements.namedItem(name)
			const hint = document.getElementById(`${name}-error`)
			if (!(input instanceof HTMLInputElement) || !hint) return false
			input.setAttribute("aria-invalid", "true")
			hint.textContent = text
			hint.hidden = false
			return true
		}

		function clearErrors() {
			feedback.hidden = true
			for (const input of form.querySelectorAll("input")) {
				input.removeAttribute("aria-invalid")
				const hint = document.getElementById(`${input.name}-error`)
				if (hint) hint.hidden = true
			}
		}

		function focusInvalid() {
			form.querySelector('[aria-invalid="true"]')?.focus()
		}

		if (isReset && !token.trim()) {
			message("Este enlace no contiene un token válido. Solicita otro enlace de recuperación.", true)
			return
		}

		let api
		try {
			;({ api } = await import("./api.js"))
		} catch {
			message("No se pudo cargar el formulario. Comprueba tu conexión y vuelve a abrir el enlace.", true)
			return
		}
		form.hidden = false
		button.disabled = false

		form.addEventListener("submit", async (event) => {
			event.preventDefault()
			if (busy) return
			clearErrors()
			const values = new FormData(form)
			let body
			if (isReset) {
				const newPassword = String(values.get("newPassword") ?? "")
				const confirmPassword = String(values.get("confirmPassword") ?? "")
				const length = Array.from(newPassword).length
				if (length < 8 || length > 72) {
					fieldError("newPassword", "La contraseña debe tener entre 8 y 72 caracteres")
				}
				if (newPassword !== confirmPassword) {
					fieldError("confirmPassword", "Las contraseñas deben coincidir")
				}
				body = { token, newPassword }
			} else {
				const email = String(values.get("email") ?? "").trim().toLowerCase()
				const input = form.elements.namedItem("email")
				if (input instanceof HTMLInputElement) {
					input.value = email
					if (!email || !input.validity.valid) {
						fieldError("email", "Escribe un correo electrónico válido")
					}
				}
				body = { email }
			}
			if (form.querySelector('[aria-invalid="true"]')) {
				focusInvalid()
				return
			}

			busy = true
			button.disabled = true
			button.textContent = isReset ? "Guardando…" : "Enviando…"
			form.setAttribute("aria-busy", "true")
			try {
				await api(isReset ? "/auth/reset-password" : "/auth/forgot-password", {
					method: "POST",
					body: JSON.stringify(body),
				}, { redirectOnUnauthorized: false })
				form.reset()
				if (isReset) {
					token = ""
					form.hidden = true
					message("Contraseña actualizada exitosamente. Inicia sesión con tu nueva contraseña.")
				} else {
					message("Si el correo está registrado, recibirás un enlace de recuperación válido por 15 minutos.")
				}
			} catch (error) {
				let hasFieldErrors = false
				if (error?.errors && typeof error.errors === "object") {
					for (const [name, entry] of Object.entries(error.errors)) {
						hasFieldErrors = fieldError(name, entry?.message ?? "Revisa este campo") || hasFieldErrors
					}
				}
				// También se acepta el formato 422 nativo de FastAPI si cambia el handler.
				if (Array.isArray(error?.detail)) {
					for (const entry of error.detail) {
						const name = entry.loc?.[entry.loc.length - 1]
						hasFieldErrors = fieldError(name, entry.msg ?? "Revisa este campo") || hasFieldErrors
					}
				}
				if (hasFieldErrors) {
					focusInvalid()
				} else if (isReset && [400, 401].includes(error?.code)) {
					message("No se pudo usar el enlace: puede ser inválido, haber expirado o ya estar usado. Solicita otro enlace.", true)
				} else {
					message("No se pudo completar la solicitud. Comprueba tu conexión e inténtalo de nuevo.", true)
				}
			} finally {
				busy = false
				button.disabled = false
				button.textContent = idleLabel
				form.removeAttribute("aria-busy")
			}
		})
	})
})()
