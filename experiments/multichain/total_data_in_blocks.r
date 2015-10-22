if (file.exists("mids_data_up.dat")) {
    # Read the data
    mids_data_up <- read.table("mids_data_up.dat", header=T, sep="\t")
    mids_data_up <- t(mids_data_up)

    # Start PDF device driver to save output to figure.pdf
    pdf(file="mids_data_up.pdf")

    matplot(mids_data_up, type=c("b"), pch=1, col= 1:4, xlab="Sequence number", ylab="Total data in MB")

    # Turn off device driver (to flush output to PDF)
    dev.off()
}

if (file.exists("mids_data_down.dat")) {
    # Read the data
    mids_data_down <- read.table("mids_data_down.dat", header=T, sep="\t")
    mids_data_down <- t(mids_data_down)

    # Start PDF device driver to save output to figure.pdf
    pdf(file="mids_data_down.pdf")

    matplot(mids_data_down, type=c("b"), pch=1, col= 1:4, xlab="Sequence number", ylab="Total data in MB")

    # Turn off device driver (to flush output to PDF)
    dev.off()
}