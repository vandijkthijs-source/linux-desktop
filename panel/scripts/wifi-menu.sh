#!/usr/bin/env bash

exec 9>"${XDG_RUNTIME_DIR:?}/linux-panel-wifi.lock"
flock -n 9 || exit 0
export LC_ALL=C

# Positie: direct onder de aangeklikte Wi-Fi-indicator.
width=350
mouse_x=$(xdotool getmouselocation --shell | sed -n 's/^X=//p')
screen_width=$(xdotool getdisplaygeometry | awk '{print $1}')

mouse_x=${POLYBAR_MENU_ANCHOR_X:-$mouse_x}
screen_width=${POLYBAR_MENU_SCREEN_WIDTH:-$screen_width}
left=${POLYBAR_MENU_SCREEN_LEFT:-0}
top=${POLYBAR_MENU_TOP:-43}
x=$((mouse_x - width / 2))
((x < left + 8)) && x=$((left + 8))
((x > left + screen_width - width - 8)) && x=$((left + screen_width - width - 8))

position="window {
    location: northwest;
    anchor: northwest;
    x-offset: ${x}px;
    y-offset: ${top}px;
    width: ${width}px;
}
listview {
    lines: 9;
}"

message() {
    notify-send "Wi-Fi" "$1"
}

# Vind de draadloze netwerkadapter.
iface=$(nmcli -t -f DEVICE,TYPE device status |
    awk -F: '$2 == "wifi" {print $1; exit}')

if [[ -z "$iface" ]]; then
    message "Geen Wi-Fi-adapter gevonden."
    exit 1
fi

state=$(nmcli radio wifi)
items=()

if [[ "$state" == "enabled" ]]; then
    current=$(nmcli -g GENERAL.CONNECTION device show "$iface")

    if [[ -n "$current" && "$current" != "--" ]]; then
        items+=("✓ Verbonden: $current")
    fi

    while IFS= read -r ssid; do
        [[ -n "$ssid" ]] && items+=("• $ssid")
    done < <(
        nmcli --escape no -g SSID device wifi list --rescan no ifname "$iface" 2>/dev/null |
        awk 'NF && !seen[$0]++'
    )

    items+=("↻ Netwerken vernieuwen")
    items+=("○ Wi-Fi uitschakelen")
else
    items+=("● Wi-Fi inschakelen")
fi

items+=("⚙ Netwerkinstellingen")

choice=$(
    printf '%s\n' "${items[@]}" |
    rofi -theme "$HOME/.config/rofi/wifi.rasi" -dmenu -no-custom -i \
        -p "Wi-Fi" -window-title "Panel Wi-Fi" -pid "$XDG_RUNTIME_DIR/linux-panel-wifi-rofi.pid" \
        -theme-str "$position"
) || exit 0

case "$choice" in
    "✓ Verbonden:"*)
        exit 0
        ;;

    "● Wi-Fi inschakelen")
        if nmcli -w 5 radio wifi on; then message "Wi-Fi ingeschakeld"; else message "Wi-Fi inschakelen mislukt"; fi
        ;;

    "○ Wi-Fi uitschakelen")
        if nmcli -w 5 radio wifi off; then message "Wi-Fi uitgeschakeld"; else message "Wi-Fi uitschakelen mislukt"; fi
        ;;

    "↻ Netwerken vernieuwen")
        if ! nmcli -w 10 device wifi rescan ifname "$iface"; then
            message "Netwerken vernieuwen mislukt"
        fi
        flock -u 9
        exec "$0"
        ;;

    "⚙ Netwerkinstellingen")
        nm-connection-editor &
        ;;

    "• "*)
        ssid="${choice#• }"

        # Try saved credentials once; request secrets only for an authentication error.
        error=$(nmcli -w 10 device wifi connect "$ssid" ifname "$iface" 2>&1)
        result=$?
        if ((result == 0)); then
            message "Verbonden met $ssid"
        elif [[ "$error" == *"Secrets were required"* || "$error" == *"password"* || "$error" == *"Password"* ]]; then
            password=$(rofi -theme "$HOME/.config/rofi/wifi.rasi" -dmenu -password -p "Wi-Fi-wachtwoord" -theme-str "$position") || exit 0
            [[ -n "$password" ]] || exit 0
            if nmcli -w 20 device wifi connect "$ssid" password "$password" ifname "$iface" >/dev/null 2>&1; then
                message "Verbonden met $ssid"
            else
                message "Verbinding mislukt. Controleer het wachtwoord of open Netwerkinstellingen."
            fi
            unset password
        else
            message "Verbinding mislukt. Controleer Netwerkinstellingen."
        fi
        ;;
esac
